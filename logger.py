import logging



def newLog(name):
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    # Create file handler for logger
    file_handler = logging.FileHandler('logs/{0}.log'.format(name),encoding='utf-16-le')
    file_handler.setLevel(logging.DEBUG)
    # Create formatter and add it to the handler
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    # Add the handler to the logger
    logger.addHandler(file_handler)
    return logger