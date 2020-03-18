from funcx.sdk.client import FuncXClient
import json

def inference_function(smiles):
    """Run inference on a list of smiles
    
    Uses multi-processing for intra-node parallelism"""
    # Launch the process pool if this is the first invocation
    #  Note: The pool will stay alive until the host process dies
    #   OK for HPC (host dies when job completes) but be very careful
    #   running this function on persistant servers.
    global pool 
    import os
    core_count = len(os.sched_getaffinity(0))
    # I use the affinity rather than `os.cpu_count()` to work with aprun's
    #  protocol for specifying the affinity of each MPI PE and all its 
    #  child processes (including those spawned by multiprocessing)
    if 'pool' not in globals():
        from multiprocessing import Pool
        pool = Pool(core_count)
    
    # Measure the start time and record host name
    from datetime import datetime
    from platform import node
    start_time = datetime.utcnow().isoformat()
    hostname = node()
    
    # Pull in the inference function and run it
    from gctox.model import invoke_model
    from gctox.features import compute_features
    import numpy as np
    n_splits = min(core_count * 2, len(smiles))
    chunks = np.array_split(smiles, n_splits)
    feats = np.concatenate(pool.map(compute_features, chunks))
    result = invoke_model(feats, smiles)
    
    # Measure the end time
    end_time = datetime.utcnow().isoformat()
    return {
        'start': start_time,
        'result': result,
        'end': end_time,
        'core_count': core_count,
        'hostname': hostname
    }

# Test run
print(inference_function(['C', 'CCCCC']))
    
# Make the client
fxc = FuncXClient()

# Register and save the function
func_uuid = fxc.register_function(inference_function, description="Infer toxicity based on Tox21 with Deepchem's Graph Convolution")
print(f'Registered function as {func_uuid}')
with open('func_uuid.json', 'w') as fp:
    json.dump(func_uuid, fp)
