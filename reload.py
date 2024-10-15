import subprocess
import os
import signal
import time

time.sleep(2)
FLAG = "RESTARTED"
dir_path = os.path.dirname(os.path.realpath(__file__))
main_script_path  = os.path.join(dir_path, 'main.py')
print(main_script_path)

def check_process(pid_file):
    try:
        with open(pid_file, 'r') as f:
            pid = f.read().strip()

        if not pid.isdigit():
            print(f"Invalid PID found in file: {pid}")
            return None

        pid = int(pid)
        os.kill(pid, 0)
        return pid
    except (FileNotFoundError, ProcessLookupError):
        return None
    except OSError as e:
        if e.winerror == 87:
            print(f"Error checking process: {e}. PID may be corrupted or invalid.")
        else:
            print(f"An error occurred while checking the process: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error when checking the process: {e}")
        return None

def terminate_main_script(pid_file):
    pid = check_process(pid_file)
    if pid:
        print(f"Terminating main script with PID: {pid}")
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(2)
        except OSError as e:
            print(f"Error terminating process: {e}")
            return False
        return True
    else:
        print("Main script is not running.")
        return False

def restart_main_script(pid_file):
    print("Restarting main script...")
    command = ['python', main_script_path, '--flag', FLAG]
    process = subprocess.Popen(command, creationflags=subprocess.CREATE_NEW_CONSOLE)
    with open(pid_file, 'w') as f:
        f.write(str(process.pid))
    print(f"Main script started with PID: {process.pid}")

pid_file = 'main_script.pid'

if terminate_main_script(pid_file):
    restart_main_script(pid_file)
else:
    restart_main_script(pid_file)
