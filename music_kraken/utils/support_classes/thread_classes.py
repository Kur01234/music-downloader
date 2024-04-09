class EndThread:
    _has_ended: bool = False
    
    def __bool__(self):
        return self._has_ended
    
    def exit(self):
        self._has_ended
        
class FinishedSearch:
    pass
        