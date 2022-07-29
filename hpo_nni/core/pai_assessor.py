# -*- encoding:utf-8 -*-
# Copyright (c) Alibaba, Inc. and its affiliates.
import logging

from hpo_nni.core.pyodps_utils import create_odps
from hpo_nni.core.utils import get_value
from hpo_nni.core.utils import set_value
from nni.algorithms.hpo.medianstop_assessor import MedianstopAssessor
from nni.assessor import AssessResult
from nni.utils import extract_scalar_history


class PAIAssessor(MedianstopAssessor):

  def assess_trial(self, trial_job_id, trial_history):
    logging.info('trial access %s %s', trial_job_id, trial_history)
    curr_step = len(trial_history)
    if curr_step < self._start_step:
      return AssessResult.Good

    scalar_trial_history = extract_scalar_history(trial_history)
    self._update_data(trial_job_id, scalar_trial_history)

    if self._high_better:
      best_history = max(scalar_trial_history)
    else:
      best_history = min(scalar_trial_history)
    avg_array = []

    for id_ in self._running_history:
      if id_ != trial_job_id:
        if len(self._running_history[id_]) >= curr_step:
          avg_array.append(self._running_history[id_][curr_step - 1])

    if avg_array:
      avg_array.sort()
      if self._high_better:
        median = avg_array[(len(avg_array) - 1) // 2]
        return AssessResult.Bad if best_history < median else AssessResult.Good
      else:
        median = avg_array[len(avg_array) // 2]
        return AssessResult.Bad if best_history > median else AssessResult.Good
    else:
      return AssessResult.Good

  def trial_end(self, trial_job_id, success):
    logging.info('trial end')
    if not success:
      logging.info('early stop kill instance')
      access_id = get_value('access_id', trial_id=trial_job_id)
      access_key = get_value('access_key', trial_id=trial_job_id)
      project = get_value('project', trial_id=trial_job_id)
      endpoint = get_value('endpoint', trial_id=trial_job_id)
      instance = get_value(trial_job_id, trial_id=trial_job_id)
      if access_id and access_key and project and endpoint and instance:
        o = create_odps(
            access_id=access_id,
            access_key=access_key,
            project=project,
            endpoint=endpoint)
        logging.info('stop instance')
        o.stop_instance(instance)
        logging.info('stop instance success')
        # for report result
        set_value(trial_job_id + '_exit', '1', trial_id=trial_job_id)