import logging



def newLog(name):
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    # Create file handler for logger
    file_handler1 = logging.FileHandler('logs/{0}.log'.format(name),encoding='utf-16-le')
    file_handler1.setLevel(logging.DEBUG)
    # Create formatter and add it to the handler
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler1.setFormatter(formatter)
    # Add the handler to the logger
    logger.addHandler(file_handler1)
    return logger