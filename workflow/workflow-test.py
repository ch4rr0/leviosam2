'''
Tests of the workflow/leviosam2.py workflow.
'''
import pathlib
import sys
import unittest

import leviosam2

TIME_CMDS = ['', 'time -v -ao test.time_log']


class Workflow(unittest.TestCase):

    def test_check_input_exists(self):
        leviosam2.check_input_exists(pathlib.Path.cwd() / sys.argv[0])
        with self.assertRaises(FileNotFoundError):
            leviosam2.check_input_exists(pathlib.Path.cwd() /
                                         f'{sys.argv[0]}-not-a-file')

    def test_run_leviosam2(self):
        raise NotImplementedError
        # leviosam2.run_leviosam2()

    def test_run_sort_committed(self):
        for time_cmd in TIME_CMDS:
            result = leviosam2.run_sort_committed(
                time_cmd=time_cmd,
                samtools='samtools',
                num_threads=4,
                out_prefix=pathlib.Path('test'),
                dryrun=True,
                forcerun=False)
            expected = (f'{time_cmd} samtools sort -@ 4 '
                        '-o test-committed-sorted.bam test-committed.bam')
            self.assertEqual(result, expected)

    def test_run_collate_pe(self):
        for time_cmd in TIME_CMDS:
            result = leviosam2.run_collate_pe(time_cmd=time_cmd,
                                              leviosam2='leviosam2',
                                              out_prefix=pathlib.Path('test'),
                                              dryrun=True,
                                              forcerun=False)
            expected = (f'{time_cmd} leviosam2 collate '
                        '-a test-committed-sorted.bam '
                        '-b test-deferred.bam -p test-paired')
            self.assertEqual(result, expected)

    def test_run_realign_deferred_pe(self):
        raise NotImplementedError
        # leviosam2.run_realign_deferred_pe()


if __name__ == '__main__':
    unittest.main()