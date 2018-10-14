
class MyDBRouter(object):

    # 
    def db_for_read(self, model, **hints):
        if model in ():
            return 'review'
        else:
            return 'default'
        return None

    def db_for_write(self, model, **hints):
        if model in ():
            return 'review'
        else:
            return 'default'
        return None
