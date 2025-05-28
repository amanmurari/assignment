import logging
import sys
from pathlib import Path
from typing import Dict, Any

def setup_logging(log_level: str = "INFO") -> None:
    """Set up logging configuration."""
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure logging format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Configure handlers
    handlers = {
        # File handler for all logs
        "file": {
            "class": "logging.FileHandler",
            "filename": "logs/workflow.log",
            "formatter": "standard",
            "level": log_level
        },
        # File handler for errors only
        "error_file": {
            "class": "logging.FileHandler",
            "filename": "logs/errors.log",
            "formatter": "detailed",
            "level": "ERROR"
        },
        # Console handler
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": log_level,
            "stream": sys.stdout
        }
    }
    
    # Configure formatters
    formatters = {
        "standard": {
            "format": log_format,
            "datefmt": date_format
        },
        "detailed": {
            "format": log_format + "\nException: %(exc_info)s",
            "datefmt": date_format
        }
    }
    
    # Configure loggers
    loggers = {
        "workflow": {
            "level": log_level,
            "handlers": ["file", "console", "error_file"],
            "propagate": False
        },
        "agents": {
            "level": log_level,
            "handlers": ["file", "console", "error_file"],
            "propagate": False
        },
        "api": {
            "level": log_level,
            "handlers": ["file", "console", "error_file"],
            "propagate": False
        }
    }
    
    # Create logging configuration
    config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": formatters,
        "handlers": handlers,
        "loggers": loggers
    }
    
    # Apply configuration
    logging.config.dictConfig(config)
    
    # Create logger instances
    workflow_logger = logging.getLogger("workflow")
    agents_logger = logging.getLogger("agents")
    api_logger = logging.getLogger("api")
    
    workflow_logger.info("Logging configuration initialized")
    return workflow_logger, agents_logger, api_logger 