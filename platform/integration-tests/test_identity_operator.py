import importlib.util
import os
from pathlib import Path

import pytest

spec=importlib.util.spec_from_file_location('identity_operator',Path(__file__).parents[2]/'operations/identity-operator.py')
operator=importlib.util.module_from_spec(spec);spec.loader.exec_module(operator)


def test_invitation_output_is_new_private_owned_and_narrow(tmp_path):
    tmp_path.chmod(0o700)
    target=tmp_path/'human-invitation-fixture.json'
    operator.validate_target(target,tmp_path,os.geteuid())
    for bad in [tmp_path/'other.json',tmp_path/'human-invitation-bad\nname.json',tmp_path/'other'/'human-invitation-fixture.json']:
        with pytest.raises(ValueError):operator.validate_target(bad,tmp_path,os.geteuid())
    tmp_path.chmod(0o750)
    with pytest.raises(ValueError):operator.validate_target(target,tmp_path,os.geteuid())
    tmp_path.chmod(0o700)
    target.touch(mode=0o600)
    with pytest.raises(ValueError):operator.validate_target(target,tmp_path,os.geteuid())
    link=tmp_path/'human-invitation-link.json';link.symlink_to(target)
    with pytest.raises(ValueError):operator.validate_target(link,tmp_path,os.geteuid())
