from pymongo import MongoClient

def drop_collections():
    client = MongoClient('mongodb://localhost:27017/')
    db = client['reservierung_db']
    
    # Listen Sie die Sammlungen auf, die Sie löschen möchten
    collections_to_drop = ['tische', 'reservierungen']
    
    for collection in collections_to_drop:
        db.drop_collection(collection)
        print(f'Dropped collection: {collection}')

if __name__ == '__main__':
    drop_collections()
