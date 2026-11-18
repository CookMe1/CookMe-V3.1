import { toMinutes, formatMinutes, totalTimeLabel } from './time';

test('reads the time formats we store', () => {
  expect(toMinutes('15 min')).toBe(15);
  expect(toMinutes('1h 30m')).toBe(90);
  expect(toMinutes('2 hrs')).toBe(120);
  expect(toMinutes('45')).toBe(45);
  expect(toMinutes(undefined)).toBe(0);
});
test('total is prep plus cook, with ~ when estimated', () => {
  expect(totalTimeLabel({ prep_time: '25 min', cook_time: '2h 30m', time_estimated: true })).toBe('~2h 55m');
  expect(totalTimeLabel({ prep_time: '10 min', cook_time: '20 min' })).toBe('30 min');
  expect(totalTimeLabel({})).toBe('—');
  expect(formatMinutes(120)).toBe('2h');
});
