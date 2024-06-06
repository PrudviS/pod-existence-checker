import time
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from dotenv import load_dotenv,find_dotenv
import sys
import os
import json

load_dotenv(find_dotenv())

def check_pod_exists_with_labels(namespace, labels):
    try:
        #config.load_kube_config() (# use for local development to set kubernetes cluster context to current context)
        config.load_incluster_config()
        v1 = client.CoreV1Api()
        label_selector = ",".join([f"{key}={value}" for key, value in labels.items()])
        pods = v1.list_namespaced_pod(namespace, label_selector=label_selector)

        for pod in pods.items:
            if pod.status.phase == "Running" and all(c.ready for c in pod.status.container_statuses):
                print(f"pod exists in namespace '{namespace}' with labels {labels} and all containers are in running state.")
                return True

        return False

    except ApiException as e:
        print(f"Exception when calling CoreV1Api->list_namespaced_pod: {e}", file=sys.stderr)
        return False

def check_pods(namespace_label_dict, timeout, interval):
    start_time = time.time()
    retry_attempt = 0
    while time.time() - start_time < timeout:
        all_found = True
        retry_attempt =  retry_attempt + 1
        print(f"Attempt {retry_attempt} - checking for pod existence")

        for namespace, labels_list in namespace_label_dict.items():
            for labels in labels_list:
                if not check_pod_exists_with_labels(namespace, labels):
                    all_found = False
                    print(f"No pod exists or pod is not ready yet in namespace '{namespace}' with labels {labels}. Retrying...")
                    break
            if not all_found:
                break

        if all_found:
            print("Pods exist and are ready in all specified namespaces with all specified labels.")
            sys.exit(0)

        time.sleep(interval)

    print("Timeout reached. No pod exists or pod is not ready with all specified labels in the specified namespaces.")
    sys.exit(1)

def main():
    namespace_label_dict = json.loads(os.getenv('NAMESPACE_LABEL_DICT', '{}'))
    if namespace_label_dict == {}:
        print("Empty namespaces and labels dictionary provided as input")
        sys.exit(0)

    timeout = int(os.getenv('TIMEOUT', 300))  # default timeout 300 seconds
    interval = int(os.getenv('RETRY_INTERVAL', 15))  # default retry interval 15 seconds

    check_pods(namespace_label_dict, timeout, interval)

if __name__ == "__main__":
    main()