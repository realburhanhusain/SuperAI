import { describe, expect, it } from 'bun:test';
import { clientApiProfiles, webUiManagementUrl } from '../src/services/clientAccess';

describe('客户端 API 接入信息', () => {
  it('生成 OpenAI、Claude 和 Gemini 三种正确格式', () => {
    const profiles = clientApiProfiles(9527, '192.168.1.8');

    expect(profiles.map((profile) => profile.id)).toEqual(['openai', 'claude', 'gemini']);
    expect(profiles[0].baseUrl).toBe('http://127.0.0.1:9527/v1');
    expect(profiles[0].lanUrl).toBe('http://192.168.1.8:9527/v1');
    expect(profiles[1].baseUrl).toBe('http://127.0.0.1:9527');
    expect(profiles[1].lanUrl).toBe('http://192.168.1.8:9527');
    expect(profiles[2].baseUrl).toBe('http://127.0.0.1:9527');
    expect(profiles[2].lanUrl).toBe('http://192.168.1.8:9527');
  });

  it('端口无效时回退到 8317，缺少局域网地址时保持为空', () => {
    const [openai] = clientApiProfiles(0);

    expect(openai.baseUrl).toBe('http://127.0.0.1:8317/v1');
    expect(openai.lanUrl).toBeNull();
  });

  it('使用当前内核端口生成 WebUI 登录地址', () => {
    expect(webUiManagementUrl(9527)).toBe(
      'http://127.0.0.1:9527/management.html#/login',
    );
    expect(webUiManagementUrl(0)).toBe(
      'http://127.0.0.1:8317/management.html#/login',
    );
  });
});
