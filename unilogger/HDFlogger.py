import pandas as pd

class HDFLogger:
    def __init__(self, filename, hdf_key='data', openmode='a'):
        self.store = pd.HDFStore(filename, openmode)
        self.key = hdf_key

    def __call__(self, values, variableprefix=''):
        df = pd.DataFrame([v.__asdict__() for v in values])
        self.store.put(self.key, df, append=True)
        self.store.flush()

    def close(self):
        self.store.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()



