- Fix timeout failure
    - Currently prevents container launches if cleanup fails
    - docker_challenges/api/api.py:112
- Autocreate connection info based on service type



# Nice to have
- Dynamic pointing
- Individual secret permissions
- Mark flags as secret (autocreate secrets)