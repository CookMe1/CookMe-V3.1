import { askConfirm } from './confirm';

test('resolves true on confirm and false on cancel, and cleans up', async () => {
  let p = askConfirm('Delete?');
  expect(document.querySelector('[data-testid="confirm-dialog"]')).not.toBeNull();
  document.querySelector('[data-testid="confirm-ok"]').click();
  expect(await p).toBe(true);
  expect(document.querySelector('[data-testid="confirm-dialog"]')).toBeNull();

  p = askConfirm('Delete?');
  document.querySelector('[data-testid="confirm-cancel"]').click();
  expect(await p).toBe(false);
});
