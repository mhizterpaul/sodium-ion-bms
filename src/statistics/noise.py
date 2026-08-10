import numpy as np

def add_measurement_noise(Y, noise_level=0.01, channel_specific=False, seed=42):
    """
    Injects noise into the measurement matrix Y.
    Supports standard Gaussian noise and channel-specific Gaussian noise.
    """
    rng = np.random.default_rng(seed)
    Y = np.array(Y)

    if channel_specific:
        sigmas = np.atleast_1d(noise_level)
        if len(sigmas) != Y.shape[1]:
            sigmas = np.resize(sigmas, Y.shape[1])
        noise = rng.normal(0.0, sigmas, size=Y.shape)
    else:
        noise = rng.normal(0.0, noise_level, size=Y.shape)

    return Y + noise
