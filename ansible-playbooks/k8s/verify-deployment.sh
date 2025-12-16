#!/bin/bash
################################################################################
# Kubernetes Deployment Verification Script
################################################################################
# This script performs comprehensive verification of the Kubernetes cluster
# deployment by testing connectivity, checking prerequisites, and validating
# cluster configuration.
#
# Run this script BEFORE deploying the cluster to verify prerequisites
# or AFTER deployment to verify cluster health.
#
# Usage:
#   ./verify-deployment.sh [pre|post]
#
#   pre  - Run pre-deployment checks (connectivity, SSH access)
#   post - Run post-deployment checks (cluster health, pod status)
################################################################################

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Cluster configuration
CONTROL_PLANES=("192.168.20.32" "192.168.20.33" "192.168.20.34")
WORKERS=("192.168.20.40" "192.168.20.41" "192.168.20.42" "192.168.20.43" "192.168.20.44" "192.168.20.45")
PRIMARY_CONTROL_PLANE="192.168.20.32"
SSH_USER="hermes-admin"

# Counter for pass/fail
PASS_COUNT=0
FAIL_COUNT=0

################################################################################
# Helper Functions
################################################################################

print_header() {
    echo -e "\n${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC} $1"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}\n"
}

print_section() {
    echo -e "\n${BLUE}═══════════════════ $1 ═══════════════════${NC}\n"
}

pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASS_COUNT++))
}

fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAIL_COUNT++))
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

################################################################################
# Pre-Deployment Checks
################################################################################

check_prerequisites() {
    print_header "PRE-DEPLOYMENT VERIFICATION"

    # Check if Ansible is installed
    print_section "Checking Ansible Installation"
    if command -v ansible &> /dev/null; then
        ANSIBLE_VERSION=$(ansible --version | head -1)
        pass "Ansible is installed: $ANSIBLE_VERSION"
    else
        fail "Ansible is not installed"
        info "Install with: sudo apt install ansible"
    fi

    # Check if inventory file exists
    print_section "Checking Inventory File"
    if [ -f "inventory.ini" ]; then
        pass "Inventory file found: inventory.ini"
    else
        fail "Inventory file not found: inventory.ini"
    fi

    # Test SSH connectivity to all nodes
    print_section "Testing SSH Connectivity"

    echo -e "${BLUE}Control Plane Nodes:${NC}"
    for ip in "${CONTROL_PLANES[@]}"; do
        if ssh -o ConnectTimeout=5 -o BatchMode=yes "${SSH_USER}@${ip}" "echo 'Connected'" &> /dev/null; then
            pass "SSH to $ip (Control Plane)"
        else
            fail "SSH to $ip (Control Plane) - Check SSH keys or connectivity"
        fi
    done

    echo -e "\n${BLUE}Worker Nodes:${NC}"
    for ip in "${WORKERS[@]}"; do
        if ssh -o ConnectTimeout=5 -o BatchMode=yes "${SSH_USER}@${ip}" "echo 'Connected'" &> /dev/null; then
            pass "SSH to $ip (Worker)"
        else
            fail "SSH to $ip (Worker) - Check SSH keys or connectivity"
        fi
    done

    # Test Python3 availability on nodes
    print_section "Checking Python3 on Nodes"

    ALL_NODES=("${CONTROL_PLANES[@]}" "${WORKERS[@]}")
    for ip in "${ALL_NODES[@]}"; do
        PYTHON_VERSION=$(ssh -o ConnectTimeout=5 "${SSH_USER}@${ip}" "python3 --version 2>&1" || echo "Not found")
        if [[ "$PYTHON_VERSION" == *"Python 3"* ]]; then
            pass "$ip has $PYTHON_VERSION"
        else
            fail "$ip - Python3 not found or not accessible"
        fi
    done

    # Check network connectivity between nodes
    print_section "Checking Inter-Node Connectivity"

    # Ping from primary control plane to all other nodes
    info "Testing connectivity from primary control plane (${PRIMARY_CONTROL_PLANE})"

    for ip in "${ALL_NODES[@]}"; do
        if [ "$ip" != "$PRIMARY_CONTROL_PLANE" ]; then
            PING_RESULT=$(ssh "${SSH_USER}@${PRIMARY_CONTROL_PLANE}" "ping -c 1 -W 2 $ip" 2>&1)
            if [[ "$PING_RESULT" == *"1 received"* ]]; then
                pass "Primary control plane can reach $ip"
            else
                fail "Primary control plane cannot reach $ip"
            fi
        fi
    done

    # Check for unique hostnames
    print_section "Verifying Unique Hostnames"

    declare -A HOSTNAMES
    for ip in "${ALL_NODES[@]}"; do
        HOSTNAME=$(ssh "${SSH_USER}@${ip}" "hostname" 2>&1)
        if [ -n "${HOSTNAMES[$HOSTNAME]}" ]; then
            fail "Duplicate hostname detected: $HOSTNAME on $ip and ${HOSTNAMES[$HOSTNAME]}"
        else
            HOSTNAMES[$HOSTNAME]=$ip
            pass "$ip has unique hostname: $HOSTNAME"
        fi
    done

    # Check system resources
    print_section "Checking System Resources"

    echo -e "${BLUE}Control Plane Nodes (Recommended: 4 CPU, 8GB RAM):${NC}"
    for ip in "${CONTROL_PLANES[@]}"; do
        CPU=$(ssh "${SSH_USER}@${ip}" "nproc" 2>&1)
        RAM=$(ssh "${SSH_USER}@${ip}" "free -g | awk '/^Mem:/{print \$2}'" 2>&1)

        if [ "$CPU" -ge 4 ] && [ "$RAM" -ge 7 ]; then
            pass "$ip - CPU: ${CPU}, RAM: ${RAM}GB ✓"
        elif [ "$CPU" -ge 2 ] && [ "$RAM" -ge 2 ]; then
            warn "$ip - CPU: ${CPU}, RAM: ${RAM}GB (meets minimum but below recommended)"
        else
            fail "$ip - CPU: ${CPU}, RAM: ${RAM}GB (below minimum requirements)"
        fi
    done

    echo -e "\n${BLUE}Worker Nodes (Recommended: 4 CPU, 8GB RAM):${NC}"
    for ip in "${WORKERS[@]}"; do
        CPU=$(ssh "${SSH_USER}@${ip}" "nproc" 2>&1)
        RAM=$(ssh "${SSH_USER}@${ip}" "free -g | awk '/^Mem:/{print \$2}'" 2>&1)

        if [ "$CPU" -ge 2 ] && [ "$RAM" -ge 2 ]; then
            pass "$ip - CPU: ${CPU}, RAM: ${RAM}GB"
        else
            fail "$ip - CPU: ${CPU}, RAM: ${RAM}GB (below minimum requirements)"
        fi
    done
}

################################################################################
# Post-Deployment Checks
################################################################################

check_deployment() {
    print_header "POST-DEPLOYMENT VERIFICATION"

    # Test kubectl access
    print_section "Testing kubectl Access"

    KUBECTL_CMD="ssh ${SSH_USER}@${PRIMARY_CONTROL_PLANE} kubectl"

    if $KUBECTL_CMD version --client &> /dev/null; then
        pass "kubectl is accessible on primary control plane"
    else
        fail "kubectl is not accessible - Check kubeconfig"
        return 1
    fi

    # Check cluster info
    print_section "Cluster Information"

    CLUSTER_INFO=$($KUBECTL_CMD cluster-info 2>&1 || echo "Failed")
    if [[ "$CLUSTER_INFO" == *"Kubernetes control plane"* ]]; then
        pass "Cluster control plane is accessible"
        echo "$CLUSTER_INFO"
    else
        fail "Cannot access cluster control plane"
    fi

    # Check node count and status
    print_section "Node Status"

    NODE_COUNT=$($KUBECTL_CMD get nodes --no-headers 2>&1 | wc -l)
    EXPECTED_NODES=9

    if [ "$NODE_COUNT" -eq "$EXPECTED_NODES" ]; then
        pass "All $EXPECTED_NODES nodes are registered"
    else
        fail "Expected $EXPECTED_NODES nodes but found $NODE_COUNT"
    fi

    # Check for Ready nodes
    READY_COUNT=$($KUBECTL_CMD get nodes --no-headers 2>&1 | grep -c " Ready " || echo 0)

    if [ "$READY_COUNT" -eq "$EXPECTED_NODES" ]; then
        pass "All $EXPECTED_NODES nodes are Ready"
    else
        fail "Only $READY_COUNT out of $EXPECTED_NODES nodes are Ready"
    fi

    # Display node details
    echo -e "\n${BLUE}Node Details:${NC}"
    $KUBECTL_CMD get nodes -o wide

    # Check control plane components
    print_section "Control Plane Components"

    components=("kube-apiserver" "kube-controller-manager" "kube-scheduler" "etcd")

    for component in "${components[@]}"; do
        POD_COUNT=$($KUBECTL_CMD get pods -n kube-system -l component=${component} --no-headers 2>&1 | wc -l)
        RUNNING_COUNT=$($KUBECTL_CMD get pods -n kube-system -l component=${component} --no-headers 2>&1 | grep -c "Running" || echo 0)

        if [ "$RUNNING_COUNT" -eq 3 ]; then
            pass "${component}: ${RUNNING_COUNT}/3 running (HA)"
        elif [ "$RUNNING_COUNT" -gt 0 ]; then
            warn "${component}: ${RUNNING_COUNT} running (expected 3 for HA)"
        else
            fail "${component}: No running pods found"
        fi
    done

    # Check Calico CNI
    print_section "Calico CNI Status"

    CALICO_NODE_COUNT=$($KUBECTL_CMD get pods -n kube-system -l k8s-app=calico-node --no-headers 2>&1 | wc -l)
    CALICO_RUNNING=$($KUBECTL_CMD get pods -n kube-system -l k8s-app=calico-node --no-headers 2>&1 | grep -c "Running" || echo 0)

    if [ "$CALICO_RUNNING" -eq "$EXPECTED_NODES" ]; then
        pass "Calico node pods: ${CALICO_RUNNING}/${EXPECTED_NODES} running"
    else
        fail "Calico node pods: Only ${CALICO_RUNNING}/${EXPECTED_NODES} running"
    fi

    CALICO_CONTROLLER=$($KUBECTL_CMD get pods -n kube-system -l k8s-app=calico-kube-controllers --no-headers 2>&1 | grep -c "Running" || echo 0)

    if [ "$CALICO_CONTROLLER" -ge 1 ]; then
        pass "Calico controller: Running"
    else
        fail "Calico controller: Not running"
    fi

    # Check system pods
    print_section "System Pods Status"

    TOTAL_SYSTEM_PODS=$($KUBECTL_CMD get pods -n kube-system --no-headers 2>&1 | wc -l)
    RUNNING_SYSTEM_PODS=$($KUBECTL_CMD get pods -n kube-system --no-headers 2>&1 | grep -c "Running" || echo 0)

    if [ "$RUNNING_SYSTEM_PODS" -eq "$TOTAL_SYSTEM_PODS" ]; then
        pass "All system pods running: ${RUNNING_SYSTEM_PODS}/${TOTAL_SYSTEM_PODS}"
    else
        fail "System pods: ${RUNNING_SYSTEM_PODS}/${TOTAL_SYSTEM_PODS} running"
    fi

    echo -e "\n${BLUE}System Pods:${NC}"
    $KUBECTL_CMD get pods -n kube-system

    # Check for warning events
    print_section "Recent Warning Events"

    WARNING_EVENTS=$($KUBECTL_CMD get events -A --field-selector type=Warning 2>&1 | tail -10)

    if [[ "$WARNING_EVENTS" == *"No resources found"* ]] || [ -z "$WARNING_EVENTS" ]; then
        pass "No recent warning events"
    else
        warn "Recent warning events found:"
        echo "$WARNING_EVENTS"
    fi

    # Test pod creation
    print_section "Testing Pod Creation"

    info "Creating test pod..."
    $KUBECTL_CMD run test-pod --image=nginx --restart=Never &> /dev/null || true
    sleep 5

    POD_STATUS=$($KUBECTL_CMD get pod test-pod -o jsonpath='{.status.phase}' 2>&1 || echo "NotFound")

    if [ "$POD_STATUS" == "Running" ]; then
        pass "Test pod is running - Pod networking functional"
    else
        warn "Test pod status: $POD_STATUS (may need more time)"
    fi

    # Cleanup test pod
    $KUBECTL_CMD delete pod test-pod &> /dev/null || true
}

################################################################################
# Main Script
################################################################################

print_header "KUBERNETES CLUSTER VERIFICATION SCRIPT"

case "${1:-pre}" in
    pre)
        info "Running pre-deployment checks..."
        check_prerequisites
        ;;
    post)
        info "Running post-deployment checks..."
        check_deployment
        ;;
    *)
        echo "Usage: $0 [pre|post]"
        echo "  pre  - Run pre-deployment checks"
        echo "  post - Run post-deployment checks"
        exit 1
        ;;
esac

################################################################################
# Summary
################################################################################

print_header "VERIFICATION SUMMARY"

TOTAL_CHECKS=$((PASS_COUNT + FAIL_COUNT))

echo -e "Total Checks: ${TOTAL_CHECKS}"
echo -e "${GREEN}Passed: ${PASS_COUNT}${NC}"
echo -e "${RED}Failed: ${FAIL_COUNT}${NC}"

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "\n${GREEN}✓ All checks passed!${NC}"
    echo -e "Cluster is ready for ${1:-pre} deployment operations.\n"
    exit 0
else
    echo -e "\n${RED}✗ Some checks failed.${NC}"
    echo -e "Please address the issues above before proceeding.\n"
    exit 1
fi
