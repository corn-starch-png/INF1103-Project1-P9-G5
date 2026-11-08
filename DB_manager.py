class DB_manager():
    @staticmethod
    def load_database(repository):
        errors, data_bundle = repository.load()
        return errors, data_bundle
    
    @staticmethod
    def save_database(repository):
        repository.save()

