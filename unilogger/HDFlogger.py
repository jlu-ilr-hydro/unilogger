import pandas as pd

class HDFLogger:
    def __init__(self, filename, hdf_key='data'):
        # self.store = pd.HDFStore(filename)
        self.filename=filename
        self.key = hdf_key

    def __call__(self, values, variableprefix=''):
        df = pd.DataFrame([v.__asdict__() for v in values])
        df.to_hdf(self.filename, self.key, append=True, index=False, data_columns=True)

    def close(self):
        ...
        # self.store.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()



