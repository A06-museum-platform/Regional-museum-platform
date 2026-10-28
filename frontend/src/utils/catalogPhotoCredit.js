import { catalogPhotoCredits } from '../data/catalogPhotoCredits.js';

// These public origins identify this project's immutable reference uploads.
// Ordinary staff uploads have different keys and do not inherit old credits.
const bases = [
  'https://jrgyhvfpgppoarxwqhmk.supabase.co/storage/v1/object/public/museum-media/',
  'https://pub-5f79a37728b6418db375cb056ccdd868.r2.dev/',
];

export function catalogPhotoCredit(src) {
  try {
    const url = new URL(src);
    const path = `${url.origin}${url.pathname}`;
    const base = bases.find(candidate => path.startsWith(candidate));
    return base ? catalogPhotoCredits[path.slice(base.length)] || null : null;
  } catch {
    return null;
  }
}
