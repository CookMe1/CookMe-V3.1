import { saveReturnPath, takeReturnPath } from './returnPath';

test('keeps a shared-link path through sign-in, once', () => {
  saveReturnPath('/share?text=https%3A%2F%2Ffb.com%2Fr%2F1');
  expect(takeReturnPath()).toBe('/share?text=https%3A%2F%2Ffb.com%2Fr%2F1');
  expect(takeReturnPath()).toBe('/dashboard');
});
test('ignores login and auth paths', () => {
  saveReturnPath('/login');
  expect(takeReturnPath()).toBe('/dashboard');
});
