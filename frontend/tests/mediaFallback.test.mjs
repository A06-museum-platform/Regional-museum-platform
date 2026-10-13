import test from 'node:test';
import assert from 'node:assert/strict';
import { mediaFallbackUrl } from '../src/utils/mediaFallback.js';

const config = { supabaseUrl: 'https://museum.supabase.co', r2PublicBase: 'https://pub-museum.r2.dev' };

test('owned images map to the identical R2 object key, including escaped filenames', () => {
  assert.equal(mediaFallbackUrl('https://museum.supabase.co/storage/v1/object/public/museum-media/Kula%20Trading.png', config),
    'https://pub-museum.r2.dev/Kula%20Trading.png');
});
test('local, third-party, wrong-bucket and already-fallback images are never redirected', () => {
  for (const url of ['/uploads/test.png', 'https://picsum.photos/test.png',
    'https://other.supabase.co/storage/v1/object/public/museum-media/test.png',
    'https://museum.supabase.co/storage/v1/object/public/private-bucket/test.png',
    'https://pub-museum.r2.dev/test.png']) assert.equal(mediaFallbackUrl(url, config), null);
});
test('missing or invalid standby configuration keeps primary-only reads', () => {
  const url = 'https://museum.supabase.co/storage/v1/object/public/museum-media/test.png';
  assert.equal(mediaFallbackUrl(url), null);
  assert.equal(mediaFallbackUrl(url, { ...config, r2PublicBase: 'invalid' }), null);
  assert.equal(mediaFallbackUrl(url, { ...config, r2PublicBase: 'http://public.invalid' }), null);
});
