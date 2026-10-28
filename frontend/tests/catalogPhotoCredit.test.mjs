import test from 'node:test';
import assert from 'node:assert/strict';
import { catalogPhotoCredits } from '../src/data/catalogPhotoCredits.js';
import { catalogPhotoCredit } from '../src/utils/catalogPhotoCredit.js';
const key = Object.keys(catalogPhotoCredits)[0];
const supabase = 'https://jrgyhvfpgppoarxwqhmk.supabase.co/storage/v1/object/public/museum-media/';
const r2 = 'https://pub-5f79a37728b6418db375cb056ccdd868.r2.dev/';
test('attribution follows the immutable image through failover and query strings', () => {
  assert.equal(catalogPhotoCredit(supabase + key + '?v=2'), catalogPhotoCredits[key]);
  assert.equal(catalogPhotoCredit(r2 + key), catalogPhotoCredits[key]);
});
test('replacement uploads and foreign origins cannot inherit reference labels', () => {
  for (const src of [supabase + 'uploads/collection-items/1/new-photo.jpg', 'https://unrelated.example/' + key,
    'https://jrgyhvfpgppoarxwqhmk.supabase.co.evil.example/storage/v1/object/public/museum-media/' + key,
    supabase + key + '/other.jpg', '', null]) assert.equal(catalogPhotoCredit(src), null);
});
