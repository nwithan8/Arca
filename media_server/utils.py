def trial_message(trial_length: int, trial_length_type: str, server_name: str, stop: bool = False):
    if stop:
        return f"Hello, your {trial_length}-{trial_length_type} trial of {server_name} has ended."
    return f"Hello, welcome to {server_name}! You have been granted a {trial_length}-{trial_length_type} trial!"