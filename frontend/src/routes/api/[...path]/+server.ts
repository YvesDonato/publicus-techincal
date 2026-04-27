import { env } from '$env/dynamic/private';
import type { RequestHandler } from './$types';

const DEFAULT_INTERNAL_BACKEND_API_URL = 'http://127.0.0.1:8000';
const HOP_BY_HOP_HEADERS = new Set([
  'connection',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'te',
  'trailer',
  'transfer-encoding',
  'upgrade'
]);

const proxy: RequestHandler = async ({ fetch, params, request, url }) => {
  const backendUrl = buildBackendUrl(params.path ?? '', url.search);
  const headers = forwardedHeaders(request.headers);
  const body = request.method === 'GET' || request.method === 'HEAD' ? undefined : await request.arrayBuffer();
  const response = await fetch(backendUrl, {
    method: request.method,
    headers,
    body,
    redirect: 'manual'
  });

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: responseHeaders(response.headers)
  });
};

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
export const OPTIONS = proxy;

function buildBackendUrl(path: string, search: string): string {
  const baseUrl = backendBaseUrl();
  const normalizedPath = path
    .split('/')
    .filter((segment) => segment.length > 0)
    .map((segment) => encodeURIComponent(segment))
    .join('/');

  return `${baseUrl}/api/${normalizedPath}${search}`;
}

function backendBaseUrl(): string {
  const configuredUrl = env.INTERNAL_BACKEND_API_URL || env.BACKEND_API_URL || DEFAULT_INTERNAL_BACKEND_API_URL;

  if (configuredUrl.startsWith('/')) {
    return DEFAULT_INTERNAL_BACKEND_API_URL;
  }

  return configuredUrl.replace(/\/$/, '');
}

function forwardedHeaders(source: Headers): Headers {
  const headers = new Headers(source);

  for (const header of HOP_BY_HOP_HEADERS) {
    headers.delete(header);
  }

  headers.delete('host');
  headers.delete('content-length');
  return headers;
}

function responseHeaders(source: Headers): Headers {
  const headers = new Headers(source);

  for (const header of HOP_BY_HOP_HEADERS) {
    headers.delete(header);
  }

  return headers;
}
