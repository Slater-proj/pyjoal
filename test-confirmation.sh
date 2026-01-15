#!/bin/bash

# Test script for confirmation system

# Colors for messages
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Enhanced confirmation function with flexible input
ask_confirmation() {
    local prompt="$1"
    local default="${2:-no}"
    local response
    
    while true; do
        if [[ "$default" == "yes" ]]; then
            echo -n -e "${YELLOW}$prompt (Yes/no): ${NC}"
        else
            echo -n -e "${YELLOW}$prompt (yes/No): ${NC}"
        fi
        
        read -r response
        
        # If empty, use default
        if [[ -z "$response" ]]; then
            response="$default"
        fi
        
        # Normalize response
        response=$(echo "$response" | tr '[:upper:]' '[:lower:]')
        
        case "$response" in
            y|yes|o|oui)
                return 0  # true
                ;;
            n|no|non)
                return 1  # false
                ;;
            *)
                echo -e "${RED}Please answer 'yes' or 'no' (y/n)${NC}"
                continue
                ;;
        esac
    done
}

echo "Testing flexible confirmation system:"
echo ""

# Test with default "no"
if ask_confirmation "Do you want to proceed with the first test?"; then
    echo -e "${GREEN}✅ You answered YES${NC}"
else
    echo -e "${RED}❌ You answered NO${NC}"
fi

echo ""

# Test with default "yes"
if ask_confirmation "Do you want to proceed with the second test?" "yes"; then
    echo -e "${GREEN}✅ You answered YES${NC}"
else
    echo -e "${RED}❌ You answered NO${NC}"
fi

echo ""
echo "Test completed!"