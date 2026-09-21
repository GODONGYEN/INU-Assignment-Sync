import path from 'node:path';

export function venvPython(root, platform = process.platform) {
  const paths = platform === 'win32' ? path.win32 : path.posix;
  return platform === 'win32' ? paths.join(root, 'Scripts', 'python.exe') : paths.join(root, 'bin', 'python3');
}

export function pythonPath(codeRoot, existing, platform = process.platform) {
  return existing ? `${codeRoot}${platform === 'win32' ? ';' : ':'}${existing}` : codeRoot;
}
