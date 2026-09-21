import test from 'node:test';
import assert from 'node:assert/strict';
import { venvPython, pythonPath } from '../electron/python-paths.js';
test('Windows paths and PYTHONPATH preserve spaces and Unicode', () => {
  assert.equal(venvPython('C:\\Users\\학생\\App Data\\.venv', 'win32'), 'C:\\Users\\학생\\App Data\\.venv\\Scripts\\python.exe');
  assert.equal(pythonPath('C:\\App', 'D:\\Lib', 'win32'), 'C:\\App;D:\\Lib');
});
test('macOS keeps existing runtime layout', () => {
  assert.equal(venvPython('/Users/test/.venv', 'darwin'), '/Users/test/.venv/bin/python3');
  assert.equal(pythonPath('/app', '/lib', 'darwin'), '/app:/lib');
});
