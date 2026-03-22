#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
Spinner class for displaying loading animations
"""

import sys
import time
import threading

class Spinner:
    """Spinner class for displaying loading animations"""
    
    def __init__(self, message="Loading...", delay=0.1):
        """
        Initialize the spinner
        
        Args:
            message: Message to display with the spinner
            delay: Delay between spinner animation frames
        """
        self.message = message
        self.delay = delay
        self.running = False
        self.thread = None
    
    def spin(self):
        """Spin the spinner animation"""
        while self.running:
            for char in '|/-\\':
                if not self.running:
                    break
                sys.stdout.write(f'\r{self.message} {char}')
                sys.stdout.flush()
                time.sleep(self.delay)
        sys.stdout.write('\r' + ' ' * (len(self.message) + 2) + '\r')
        sys.stdout.flush()
    
    def __enter__(self):
        """Start the spinner when entering context"""
        self.running = True
        self.thread = threading.Thread(target=self.spin, daemon=True)
        self.thread.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop the spinner when exiting context"""
        self.running = False
        if self.thread:
            self.thread.join()
