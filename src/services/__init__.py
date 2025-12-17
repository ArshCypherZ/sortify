from .execution import ExecutionService

def start_all_services():
    services = [
        ExecutionService()
    ]
    
    for service in services:
        service.start()
    
    return services
