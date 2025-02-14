from collections import defaultdict
from typing import List, Dict
import hashlib
import time

class AltMessageChecker:
    def __init__(self, time_window: int = 3600):
        self.time_window = time_window 
        self.fingerprints = defaultdict(list)
        self.exact_matches = defaultdict(set)
        
    def _create_fingerprint(self, content: str) -> str:
        if len(content) < 1000:
            return ""
            
        start = content[:100].strip().lower()
        end = content[-100:].strip().lower()
        
        return hashlib.sha256(f"{start}{end}".encode()).hexdigest()[:16]
    
    def check_alt_account(self, api_key: str, current_messages: List[Dict[str, str]]) -> bool:
        current_time = time.time()
        
        self._cleanup_old_fingerprints(current_time)
        
        message_fingerprints = set()
        for msg in current_messages:
            fingerprint = self._create_fingerprint(msg['content'])
            if fingerprint: 
                message_fingerprints.add(fingerprint)
        
        if not message_fingerprints:
            return False
        
        matches_found = 0
        suspect_keys = set()
        
        for fingerprint in message_fingerprints:
            for stored_key, timestamp in self.fingerprints[fingerprint]:
                if stored_key != api_key:
                    matches_found += 1
                    suspect_keys.add(stored_key)
                    self.exact_matches[api_key].add(stored_key)
                    self.exact_matches[stored_key].add(api_key)
            
            self.fingerprints[fingerprint].append((api_key, current_time))
        
        return len(self.exact_matches[api_key]) > 0 and matches_found >= 2
    
    def _cleanup_old_fingerprints(self, current_time: float) -> None:
        for fingerprint in list(self.fingerprints.keys()):
            self.fingerprints[fingerprint] = [
                (key, ts) for key, ts in self.fingerprints[fingerprint]
                if current_time - ts <= self.time_window
            ]
            if not self.fingerprints[fingerprint]:
                del self.fingerprints[fingerprint]

alt_message_checker: AltMessageChecker = AltMessageChecker(1800) # 30 min