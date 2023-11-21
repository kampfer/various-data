import subprocess
import os
import sys

def execute(cmd):
  subprocess.run(cmd)
  # subprocess.run(cmd, shell=True)

if __name__ == '__main__':
  python_path = os.path.join(os.path.dirname(__file__), 'subprogram.py')
  print(python_path)
  execute(['python', python_path])