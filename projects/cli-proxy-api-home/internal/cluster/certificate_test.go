package cluster

import (
	"context"
	"crypto/rand"
	"crypto/rsa"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"net"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

const clusterTLSHandshakeDeadline = 2 * time.Second

func TestCreateServerCertificateSupportsNodeMTLS(t *testing.T) {
	t.Parallel()

	now := time.Unix(100, 0).UTC()
	caPEM, caKeyPEM, _, errCA := createCACertificate(now)
	if errCA != nil {
		t.Fatalf("createCACertificate() error = %v", errCA)
	}
	caCert, errCACert := parseCertificatePEM(caPEM)
	if errCACert != nil {
		t.Fatalf("parseCertificatePEM(ca) error = %v", errCACert)
	}
	caKey, errCAKey := parseRSAPrivateKeyPEM(caKeyPEM)
	if errCAKey != nil {
		t.Fatalf("parseRSAPrivateKeyPEM(ca) error = %v", errCAKey)
	}
	serverPEM, _, _, errServer := createServerCertificate(now, caCert, caKey, "127.0.0.1")
	if errServer != nil {
		t.Fatalf("createServerCertificate() error = %v", errServer)
	}
	serverCert, errServerCert := parseCertificatePEM(serverPEM)
	if errServerCert != nil {
		t.Fatalf("parseCertificatePEM(server) error = %v", errServerCert)
	}
	if !hasExtKeyUsage(serverCert, x509.ExtKeyUsageServerAuth) {
		t.Fatal("server certificate missing server auth usage")
	}
	if !hasExtKeyUsage(serverCert, x509.ExtKeyUsageClientAuth) {
		t.Fatal("server certificate missing client auth usage")
	}
}

func TestTLSConfigFromCertificateRecordsSetsRootCAs(t *testing.T) {
	t.Parallel()

	now := time.Unix(100, 0).UTC()
	caPEM, caKeyPEM, caSerial, errCA := createCACertificate(now)
	if errCA != nil {
		t.Fatalf("createCACertificate() error = %v", errCA)
	}
	caCert, errCACert := parseCertificatePEM(caPEM)
	if errCACert != nil {
		t.Fatalf("parseCertificatePEM(ca) error = %v", errCACert)
	}
	caKey, errCAKey := parseRSAPrivateKeyPEM(caKeyPEM)
	if errCAKey != nil {
		t.Fatalf("parseRSAPrivateKeyPEM(ca) error = %v", errCAKey)
	}
	serverPEM, serverKeyPEM, serverSerial, errServer := createServerCertificate(now, caCert, caKey, "127.0.0.1")
	if errServer != nil {
		t.Fatalf("createServerCertificate() error = %v", errServer)
	}
	tlsConfig, errTLS := tlsConfigFromCertificateRecords(
		&CertificateRecord{CertificatePEM: string(caPEM), PrivateKeyPEM: string(caKeyPEM), SerialNumber: caSerial, IsCA: true},
		&CertificateRecord{CertificatePEM: string(serverPEM), PrivateKeyPEM: string(serverKeyPEM), SerialNumber: serverSerial, IsServer: true, IP: "127.0.0.1"},
	)
	if errTLS != nil {
		t.Fatalf("tlsConfigFromCertificateRecords() error = %v", errTLS)
	}
	if tlsConfig.RootCAs == nil {
		t.Fatal("RootCAs = nil, want cluster CA pool")
	}
	if tlsConfig.ClientCAs == nil {
		t.Fatal("ClientCAs = nil, want cluster CA pool")
	}
}

func TestClusterTLSRejectsDeletedClientCertificate(t *testing.T) {
	t.Parallel()

	ctx := context.Background()
	db, errOpen := OpenSQLite(ctx, filepath.Join(t.TempDir(), "home.db"))
	if errOpen != nil {
		t.Fatalf("OpenSQLite() error = %v", errOpen)
	}
	sqlDB, errDB := db.DB()
	if errDB != nil {
		t.Fatalf("DB() error = %v", errDB)
	}
	t.Cleanup(func() {
		if errClose := sqlDB.Close(); errClose != nil {
			t.Errorf("close sqlite db: %v", errClose)
		}
	})
	if errMigrate := AutoMigrate(db); errMigrate != nil {
		t.Fatalf("AutoMigrate() error = %v", errMigrate)
	}
	repo := NewRepository(db)
	serverTLS, errServerTLS := repo.EnsureClusterCertificates(ctx, "127.0.0.1")
	if errServerTLS != nil {
		t.Fatalf("EnsureClusterCertificates() error = %v", errServerTLS)
	}

	certificateID, enrollmentSecret, errPending := repo.CreatePendingClientCertificate(ctx)
	if errPending != nil {
		t.Fatalf("CreatePendingClientCertificate() error = %v", errPending)
	}
	clientKey, clientCSR := createClientCSR(t, certificateID)
	clientCertPEM, caPEM, errSign := repo.SignClientCertificateRequest(ctx, certificateID, enrollmentSecret, clientCSR)
	if errSign != nil {
		t.Fatalf("SignClientCertificateRequest() error = %v", errSign)
	}
	fingerprint, errFingerprint := certificateFingerprintPEM(clientCertPEM)
	if errFingerprint != nil {
		t.Fatalf("certificateFingerprintPEM() error = %v", errFingerprint)
	}
	if active, errActive := repo.ClientCertificateFingerprintActive(ctx, certificateID, fingerprint); errActive != nil || !active {
		t.Fatalf("ClientCertificateFingerprintActive(issued) = %v, %v", active, errActive)
	}
	if active, errActive := repo.ClientCertificateFingerprintActive(ctx, certificateID, strings.Repeat("0", 64)); errActive != nil || active {
		t.Fatalf("ClientCertificateFingerprintActive(mismatch) = %v, %v", active, errActive)
	}
	clientTLS := clientTLSConfig(t, clientCertPEM, encodeRSAPrivateKeyPEM(clientKey), caPEM)

	if errHandshake := runTLSHandshake(t, serverTLS, clientTLS); errHandshake != nil {
		t.Fatalf("handshake with issued certificate error = %v", errHandshake)
	}
	if errDelete := db.Where("id = ?", certificateID).Delete(&CertificateRecord{}).Error; errDelete != nil {
		t.Fatalf("delete client certificate record error = %v", errDelete)
	}
	if active, errActive := repo.ClientCertificateFingerprintActive(ctx, certificateID, fingerprint); errActive != nil || active {
		t.Fatalf("ClientCertificateFingerprintActive(deleted) = %v, %v", active, errActive)
	}
	if errHandshake := runTLSHandshake(t, serverTLS, clientTLS); errHandshake == nil {
		t.Fatal("handshake with deleted certificate error = nil, want failure")
	}
}

func createClientCSR(t *testing.T, commonName string) (*rsa.PrivateKey, []byte) {
	t.Helper()
	key, errKey := rsa.GenerateKey(rand.Reader, certificateKeyBits)
	if errKey != nil {
		t.Fatalf("GenerateKey() error = %v", errKey)
	}
	template := &x509.CertificateRequest{
		Subject: pkix.Name{
			CommonName: commonName,
		},
	}
	der, errCreate := x509.CreateCertificateRequest(rand.Reader, template, key)
	if errCreate != nil {
		t.Fatalf("CreateCertificateRequest() error = %v", errCreate)
	}
	return key, pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE REQUEST", Bytes: der})
}

func clientTLSConfig(t *testing.T, certPEM []byte, keyPEM []byte, caPEM []byte) *tls.Config {
	t.Helper()
	certPair, errPair := tls.X509KeyPair(certPEM, keyPEM)
	if errPair != nil {
		t.Fatalf("X509KeyPair() error = %v", errPair)
	}
	caPool := x509.NewCertPool()
	if !caPool.AppendCertsFromPEM(caPEM) {
		t.Fatal("AppendCertsFromPEM(ca) = false")
	}
	return &tls.Config{
		MinVersion:   tls.VersionTLS12,
		Certificates: []tls.Certificate{certPair},
		RootCAs:      caPool,
		ServerName:   "127.0.0.1",
	}
}

func runTLSHandshake(t *testing.T, serverConfig *tls.Config, clientConfig *tls.Config) error {
	t.Helper()
	serverConn, clientConn := net.Pipe()
	defer func() {
		if errClose := serverConn.Close(); errClose != nil {
			t.Logf("server conn close error: %v", errClose)
		}
	}()
	defer func() {
		if errClose := clientConn.Close(); errClose != nil {
			t.Logf("client conn close error: %v", errClose)
		}
	}()
	deadline := time.Now().Add(clusterTLSHandshakeDeadline)
	if errSetDeadline := serverConn.SetDeadline(deadline); errSetDeadline != nil {
		t.Fatalf("server conn set deadline error = %v", errSetDeadline)
	}
	if errSetDeadline := clientConn.SetDeadline(deadline); errSetDeadline != nil {
		t.Fatalf("client conn set deadline error = %v", errSetDeadline)
	}

	serverTLS := tls.Server(serverConn, serverConfig)
	clientTLS := tls.Client(clientConn, clientConfig)
	errCh := make(chan error, 2)
	go func() {
		errCh <- serverTLS.Handshake()
	}()
	go func() {
		errCh <- clientTLS.Handshake()
	}()

	var firstErr error
	for i := 0; i < 2; i++ {
		if errHandshake := <-errCh; errHandshake != nil && firstErr == nil {
			firstErr = errHandshake
		}
	}
	return firstErr
}
