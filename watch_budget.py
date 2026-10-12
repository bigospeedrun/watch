"""Limits for data-only watch passes. Pending work belongs in their reports."""
import time

class BudgetExhausted(RuntimeError):
    pass

class WatchBudget:
    def __init__(self,requests,seconds,api,content):
        self.limit=requests
        self.started=time.monotonic()
        self.deadline=self.started+seconds
        self.requests=0
        self.api=api
        self.content=content

    def check(self):
        if self.requests>=self.limit or time.monotonic()>=self.deadline:
            raise BudgetExhausted('Other bounds request/time budget exhausted; pending work saved')

    def call(self,fn,*args):
        self.check()
        self.requests+=1
        return fn(*args,deadline=min(self.deadline,time.monotonic()+20))

    def get(self,path,params=None):
        return self.call(self.api,path,params)

    def read(self,repo,path,head):
        return self.call(self.content,repo,path,head)

    def pause(self,seconds):
        self.check()
        if time.monotonic()+seconds>=self.deadline:
            raise BudgetExhausted('Other bounds time budget exhausted before search delay')
        time.sleep(seconds)
