#!/usr/bin/env python3
"""
Simple test script for Phase 1 & 2 - Client file validation
Tests JOAL client file format without requiring full application dependencies
"""
import json
import re
import os
from pathlib import Path

CLIENTS_DIR = Path(__file__).parent / "clients"

def parse_char_class(char_class: str) -> str:
    """Parse regex character class like A-Za-z0-9_~"""
    chars = ""
    i = 0
    while i < len(char_class):
        if i + 2 < len(char_class) and char_class[i + 1] == '-':
            start = char_class[i]
            end = char_class[i + 2]
            chars += ''.join(chr(c) for c in range(ord(start), ord(end) + 1))
            i += 3
        elif char_class[i] == '\\' and i + 1 < len(char_class):
            chars += char_class[i + 1]
            i += 2
        else:
            chars += char_class[i]
            i += 1
    return chars

def test_peer_id_pattern(pattern: str) -> tuple[bool, str]:
    """Test if peer_id pattern generates 20 bytes"""
    match = re.match(r'^([^[]+)\[([^\]]+)\]\{(\d+)\}$', pattern)
    if not match:
        return False, f"Pattern not parseable: {pattern}"
    
    prefix = match.group(1)
    length = int(match.group(3))
    total_length = len(prefix) + length
    
    if total_length != 20:
        return False, f"Total length {total_length} != 20 (prefix={len(prefix)}, suffix={length})"
    
    return True, f"OK (prefix={len(prefix)}, suffix={length})"

def validate_client_file(filepath: Path) -> dict:
    """Validate a .client file against JOAL format"""
    results = {
        "name": filepath.name,
        "valid": True,
        "errors": [],
        "warnings": [],
        "info": []
    }
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        results["valid"] = False
        results["errors"].append(f"Invalid JSON: {e}")
        return results
    
    # Check required fields
    required_fields = ["name", "version"]
    for field in required_fields:
        if field not in config:
            results["warnings"].append(f"Missing field: {field}")
    
    # Check keyGenerator
    if "keyGenerator" not in config:
        results["errors"].append("Missing keyGenerator (JOAL format required)")
        results["valid"] = False
    else:
        kg = config["keyGenerator"]
        if "algorithm" not in kg:
            results["errors"].append("keyGenerator missing algorithm")
        else:
            algo = kg["algorithm"]
            algo_type = algo.get("type", "UNKNOWN")
            results["info"].append(f"Key algorithm: {algo_type}")
            
            if algo_type == "HASH_NO_LEADING_ZERO":
                if "length" not in algo:
                    results["warnings"].append("keyGenerator.algorithm missing 'length'")
            elif algo_type == "DIGIT_RANGE_TRANSFORMED_TO_HEX_WITHOUT_LEADING_ZEROES":
                if "inclusiveLowerBound" not in algo or "inclusiveUpperBound" not in algo:
                    results["warnings"].append("keyGenerator.algorithm missing bounds")
    
    # Check peerIdGenerator
    if "peerIdGenerator" not in config:
        results["errors"].append("Missing peerIdGenerator (JOAL format required)")
        results["valid"] = False
    else:
        pg = config["peerIdGenerator"]
        if "algorithm" not in pg:
            results["errors"].append("peerIdGenerator missing algorithm")
        else:
            algo = pg["algorithm"]
            algo_type = algo.get("type", "UNKNOWN")
            results["info"].append(f"PeerId algorithm: {algo_type}")
            
            if algo_type == "REGEX":
                pattern = algo.get("pattern", "")
                ok, msg = test_peer_id_pattern(pattern)
                if ok:
                    results["info"].append(f"PeerId pattern: {msg}")
                else:
                    results["errors"].append(f"PeerId pattern error: {msg}")
                    results["valid"] = False
            elif algo_type == "RANDOM_POOL_WITH_CHECKSUM":
                prefix = algo.get("prefix", "")
                if len(prefix) != 8:
                    results["warnings"].append(f"Transmission prefix length {len(prefix)} (expected 8)")
                results["info"].append(f"PeerId prefix: {prefix}")
    
    # Check urlEncoder
    if "urlEncoder" not in config:
        results["warnings"].append("Missing urlEncoder (using defaults)")
    else:
        ue = config["urlEncoder"]
        results["info"].append(f"URL hex case: {ue.get('encodedHexCase', 'lower')}")
    
    # Check query template
    if "query" not in config:
        results["errors"].append("Missing query template (JOAL format required)")
        results["valid"] = False
    else:
        query = config["query"]
        # Check required placeholders
        required_placeholders = ["{infohash}", "{peerid}", "{port}", "{uploaded}", "{downloaded}", "{left}"]
        for ph in required_placeholders:
            if ph not in query:
                results["errors"].append(f"Query missing placeholder: {ph}")
                results["valid"] = False
        
        # Check info_hash is first (most trackers expect this)
        if not query.startswith("info_hash="):
            results["warnings"].append("Query doesn't start with info_hash (some trackers may reject)")
        
        results["info"].append(f"Query length: {len(query)} chars")
    
    # Check requestHeaders format
    if "requestHeaders" in config:
        headers = config["requestHeaders"]
        if isinstance(headers, list):
            results["info"].append(f"Headers: {len(headers)} (array format ✓)")
            for h in headers:
                if "name" not in h or "value" not in h:
                    results["warnings"].append("Header missing name or value")
        elif isinstance(headers, dict):
            results["warnings"].append("Headers in old dict format (should be array)")
    
    # Check numwant
    if "numwant" in config:
        results["info"].append(f"numwant: {config['numwant']}")
    if "numwantOnStop" in config:
        results["info"].append(f"numwantOnStop: {config['numwantOnStop']}")
    
    return results


def main():
    print("🧪 PyJOAL Client File Validator")
    print("Checking JOAL-compatible format\n")
    
    if not CLIENTS_DIR.exists():
        print(f"❌ Clients directory not found: {CLIENTS_DIR}")
        return 1
    
    client_files = list(CLIENTS_DIR.glob("*.client"))
    print(f"📁 Found {len(client_files)} client files\n")
    
    all_valid = True
    
    for filepath in sorted(client_files):
        results = validate_client_file(filepath)
        
        status = "✅" if results["valid"] else "❌"
        print(f"{status} {results['name']}")
        
        for info in results["info"]:
            print(f"   ℹ️  {info}")
        
        for warning in results["warnings"]:
            print(f"   ⚠️  {warning}")
        
        for error in results["errors"]:
            print(f"   ❌ {error}")
        
        if not results["valid"]:
            all_valid = False
        
        print()
    
    print("=" * 60)
    if all_valid:
        print("🎉 All client files are valid JOAL format!")
    else:
        print("⚠️  Some client files have issues")
    
    return 0 if all_valid else 1


if __name__ == "__main__":
    exit(main())
