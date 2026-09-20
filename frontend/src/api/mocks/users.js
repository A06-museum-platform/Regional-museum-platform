/**
 * Demo accounts for the prototype.
 *
 * Real password hashing lives in Ray's backend (bcrypt, per the contract).
 * These plaintext passwords exist only so the three roles can be demonstrated
 * without a running API, and the whole file is skipped when VITE_USE_MOCKS is
 * false. Do not copy this pattern anywhere near real credentials.
 */

export const DEMO_USERS = [
  {
    id: 'u-0001',
    email: 'eleanor.vance@example.com',
    password: 'demo1234',
    full_name: 'Eleanor Vance',
    role: 'member',
    is_active: true,
  },
  {
    id: 'u-0002',
    email: 'xuan.meng@sarhn.example.com',
    password: 'demo1234',
    full_name: 'Xuan Meng',
    role: 'staff',
    is_active: true,
  },
  {
    id: 'u-0003',
    email: 'kangjun@sarhn.example.com',
    password: 'demo1234',
    full_name: 'Kangjun Liao',
    role: 'admin',
    is_active: true,
  },
];
