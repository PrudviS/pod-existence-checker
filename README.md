# Handling pod startup dependencies in kubernetes workloads

This repository contains a python script and dockerfile for checking the existence of pods with specific labels across multiple namespaces in a Kubernetes cluster. The script is intended to be used as an init container in Kubernetes deployments to ensure that all required pods are up and running before starting the main application.

## Background

I was recently troubleshooting an issue with an application hosted on a kubernetes cluster. The issue with this application is that when the kubernetes cluster gets restarted or nodes get scaled or recycled as part of scaling or patching operations, application tends to have intermittent startup issues.

The application consists of several microservices, all hosted on the same kubernetes cluster and these individual microservices need to start up in the correct order for the application to work. You would expect these microservices to be either loosely coupled in a microservice architecture or the application has built in provisions to handle the dependencies via retries,timeouts or readiness and startup probes, but the application doesn’t handle these dependencies very well.

I am aware that there are other correct ways to address this issue, but given that i don’t have access to the application code and other limitations, I had to work around the issue.

I initially started looking at specifying pod start up dependencies using kubernetes primitives, but did not find much on this. I then considered using readiness/liveness/startup probes. I briefly considered going down the route of implementing custom kube-scheduler but we are on a managed kubernetes service from a cloud provider . I’m not sure if the cloud provider offers the support for this. I eventually settled down on writing a python script to address this issue. The idea is to run this as init container, which runs to completion prior to the application pod and checks if a pod exists and is in ready state , for specified labels and namespace as input.


## Python script

The python script src/main.py  uses the Kubernetes Python client to check for the existence of pods with specified labels in a given namespace and are in ready state. It retries within a specified timeout period to ensure all required pods are ready.

The .env file is used for testing the script during development

The idea is to run this as an init container, to check for the existence of dependent pods in ready state with specified labels in given namespaces.The script retries within a specified timeout period to ensure all required pods are ready.

## Dockerfile

The dockerfile in the repository packages the application as docker image. The image will need to be built and pushed to the container registry

## Kubernetes cluster role and role bindings

The file ns-sa-clusterrole-clusterrolebinding.yml contains the kubernetes manifests for creating the namespace, service account, cluster role with get and list pods privileges and a cluster role binding to add this role to the service account

You could do this with either cluster role and a rolebinding or a role and rolebinding but this would mean duplicating these across namespaces

## Sample deployment

The list of namespaces and labels are supplied to the deployment using an environment variable as json string. In the example deployment below, I used nginx as main application but this could be any application

The init container fails if it cannot find the pods in ready state with specified labels in the given namespace within the timeout and consequently the main application container doesn't get initialised. Once the pod is marked as init error, Kubernetes deployment controller will attempt to restart the pod. This will continue until the pods with specified labels are found


```yaml

apiVersion: apps/v1
kind: Deployment
metadata:
  name: pod-existence-checker-deployment
  namespace: pod-existence-checker
spec:
  replicas: 1
  selector:
    matchLabels:
      app: pod-existence-checker
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 1
  template:
    metadata:
      labels:
        app: pod-existence-checker
    spec:
      serviceAccountName: pod-existence-checker-sa
      automountServiceAccountToken: true
      hostPID: false
      hostIPC: false
      hostNetwork: false
      securityContext:
        runAsUser: 10001
        runAsGroup: 10001
        fsGroup: 10001
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault
        seLinuxOptions:
      initContainers:
      - name: check-pod-exists
        image: << your container registry repository >>/pod-existence-checker:<image tag>
        command: ["python", "/scripts/main.py"]
        env:
        - name: NAMESPACE_LABEL_DICT
          value: '{"namespace-1": [{"app": "MyApp", "environment": "dev"}], "namespace-2": [{"app": "MyApp", "environment": "dev"}]}'
        - name: TIMEOUT
          value: "300"
        - name: RETRY_INTERVAL
          value: "15"
        resources:
          requests:
            memory: "100Mi"
            cpu: "50m"
          limits:
            memory: "100Mi"
            cpu: "100m"
      containers:
      - name: nginx
        image: nginxinc/nginx-unprivileged:latest
        resources:
          requests:
            memory: "100Mi"
            cpu: "50m"
          limits:
            memory: "100Mi"
            cpu: "100m"