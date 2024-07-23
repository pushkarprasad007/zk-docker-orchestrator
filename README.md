This repo serves as a way to achieve 'simple' orchaestration of run 'exactly once' some containers when there's auto scaling of instances running a stack. 

## Create an image for sleeping-image 
#### NOTE : has to be done once only if image doesnt exist already

1. Go to services/loop-service
2. Run command `docker build -t sleeper-image .`

This is the image whose exactly one running container should exist across multiple (auto scaled) instances

## Running Zookeeper:

1. Go to services/zookeeper
2. Run the command `docker-compose up -d`

## Simulate 3 servers running one (daemon) container each  
#### The job of this daemon process is to get Lock from ZK and then start the sleeping-image

1. Go to services/app<1/2/3>
2. Run `docker compose up -d`

Once all the "app" containers are running, one of them would be able to get the Lock on zk, and start the sleeping-image container. Others app services will keep on trying to get lock, but will fail until the app service which got lock releases it somehow.
Now take down one of the app service. It should result in lock getting released (also the sleeping-image container would stop) and another app service should be able to get the lock. 

This simulates how the locking can be done using zk, and that can allow us to run a code / service exactly one instance of. Of course zookeeper gives other constructs where in we can achieve exactly 1/2/3 etc also, using shared synchronous data.
