import os
import time
import docker
import signal
import sys
from kazoo.client import KazooClient
from kazoo.exceptions import NodeExistsError, LockTimeout
from datetime import datetime

def signal_handler(sig, frame):
    print(f"[{datetime.now()}] Received shutdown signal, cleaning up...")
    cleanup()
    sys.exit(0)

def cleanup():
    global docker_client
    if docker_client:
        stop_sleeper_image(docker_client)
    print(f"[{datetime.now()}] Cleanup complete.", flush=True)

def start_sleeper_image(docker_client):
    try:
        container = docker_client.containers.get('sleeper-image')
        if container.status != 'running':
            container.start()
            print(f"[{datetime.now()}] Started sleeper_image container", flush=True)
    except docker.errors.NotFound:
        docker_client.containers.run('sleeper-image', name='sleeper-image', detach=True)
        print(f"[{datetime.now()}] Created and started sleeper_image container", flush=True)

def stop_sleeper_image(docker_client):
    try:
        container = docker_client.containers.get('sleeper-image')
        if container.status == 'running':
            container.stop()
            print(f"[{datetime.now()}] Stopped sleeper-image container", flush=True)
    except docker.errors.NotFound:
        print(f"[{datetime.now()}] sleeper-image container not found", flush=True)

def main():
    global docker_client
    
    # Get ZooKeeper hosts from environment variable
    zk_hosts = os.environ.get('ZOOKEEPER_HOSTS', 'localhost:2181')
    print(zk_hosts, flush=True)
    
    # Connect to ZooKeeper
    zk = KazooClient(hosts=zk_hosts)
    zk.start()

    # Connect to Docker
    docker_client = docker.from_env()

    # Ensure the lock path exists
    zk.ensure_path("/locks")

    # Create the lock object
    lock_path = "/locks/my_lock"
    lock = zk.Lock(lock_path)

    while True:
        try:
            # Try to acquire the lock with a timeout
            lock_acquired = lock.acquire(timeout=10)  # 10 seconds timeout
            
            if lock_acquired:
                print(f"[{datetime.now()}] Lock acquired!", flush=True)
                # Critical section
                print(f"[{datetime.now()}] Entering critical section...", flush=True)
                start_sleeper_image(docker_client)
                try:
                    while lock.is_acquired:
                        # Simulate some work
                        time.sleep(5)
                        print(f"[{datetime.now()}] Still in critical section...", flush=True)
                except Exception as e:
                    # Stop sleeper-image container
                    stop_sleeper_image(docker_client)
                    raise e

                print(f"[{datetime.now()}] Exiting critical section...", flush=True)
            else:
                print(f"[{datetime.now()}] Failed to acquire lock, will try again...", flush=True)
        
        except LockTimeout:
            print(f"[{datetime.now()}] Lock acquisition timed out, will try again...", flush=True)
        
        except Exception as e:
            print(f"[{datetime.now()}] An error occurred: {str(e)}", flush=True)
        
        finally:
            # Always attempt to release the lock and stop the container
            if lock.is_acquired:
                lock.release()
                print(f"[{datetime.now()}] Lock released", flush=True)
                # Stop sleeper-image container
                stop_sleeper_image(docker_client)
            
            # Sleep before trying again
            sleep_time = 5  # 5 seconds sleep
            print(f"[{datetime.now()}] Sleeping for {sleep_time} seconds before trying again...", flush=True)
            time.sleep(sleep_time)

if __name__ == "__main__":
    docker_client = None
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    try:
        main()
    finally:
        cleanup()