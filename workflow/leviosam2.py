'''
Nae-Chyun Chen
Johns Hopkins University
2021-2022
'''

import argparse
import pathlib
import subprocess
import typing


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('--leviosam2_binary',
                        default='leviosam2',
                        type=str,
                        help='Path to the leviosam2 executable')
    parser.add_argument('--samtools_binary',
                        default='samtools',
                        type=str,
                        help='Path to the samtools executable')
    parser.add_argument('--bgzip_binary',
                        default='bgzip',
                        type=str,
                        help='Path to the bgzip executable')
    parser.add_argument('--gnu_time_binary',
                        default='gtime',
                        type=str,
                        help=('Path to the GNU Time executable '
                              '(see https://www.gnu.org/software/time/)'))
    parser.add_argument('--measure_time',
                        action='store_true',
                        help=('Activate to measure time with '
                              '`--gnu_time_binary`'))
    parser.add_argument('--keep_tmp_files',
                        action='store_true',
                        help=('Activate to keep temp files '
                              'generated by the workflow'))
    parser.add_argument('-t',
                        '--num_threads',
                        type=int,
                        default=4,
                        help='Number of threads to use')
    parser.add_argument('--sequence_type',
                        type=str,
                        required=True,
                        choices=['ilmn_pe', 'ilmn_se', 'pb_hifi', 'ont'],
                        help='Type of sequence data')
    parser.add_argument('-a',
                        '--aligner',
                        type=str,
                        required=True,
                        choices=[
                            'bowtie2', 'bwamem', 'bwamem2', 'minimap2',
                            'winnowmap2', 'strobealign'
                        ])
    parser.add_argument('--aligner_binary',
                        type=str,
                        default='auto',
                        help=('Path to the aligner executable. '
                              'If empty, inferred using `--aligner`'))
    parser.add_argument('--source_label',
                        type=str,
                        default='source',
                        help='Label of the source reference')
    parser.add_argument('--target_label',
                        type=str,
                        default='target',
                        help='Label of the target reference')
    parser.add_argument('--read_group', type=str, help='Read group string')
    parser.add_argument('-g',
                        '--lift_max_gap',
                        type=int,
                        help='[lift] Max chain gap size allowed')
    parser.add_argument('--lift_commit_min_mapq',
                        type=int,
                        help='[lift] Min MAPQ to commit')
    parser.add_argument('--lift_commit_min_score',
                        type=int,
                        help='[lift] Min alignment score (AS:i tag) to commit')
    parser.add_argument('--lift_commit_max_frac_clipped',
                        type=float,
                        help='[lift] Min fraction of clipped bases to commit')
    parser.add_argument('--lift_commit_max_isize',
                        type=int,
                        help='[lift] Max template length (isize) to commit')
    parser.add_argument('--lift_commit_max_hdist',
                        type=int,
                        help='[lift] Max edit distance (NM:i tag) to commit')
    parser.add_argument('--lift_bed_commit_source',
                        type=str,
                        help=('[lift] Path to a BED (source coordinates) '
                              'where reads in the regions are always '
                              'committed (often for suppress annotations)'))
    parser.add_argument('--lift_bed_defer_target',
                        type=str,
                        help=('[lift] Path to a BED (target cooridnates'
                              'where reads in the regions are always '
                              'deferred'))
    parser.add_argument('--lift_realign_config',
                        type=str,
                        help=('[lift] Path to the config file for '
                              'realignment'))
    parser.add_argument('-i',
                        '--input_alignment',
                        type=str,
                        required=True,
                        help='Path to the input SAM/BAM/CRAM file')
    parser.add_argument('-o',
                        '--out_prefix',
                        type=str,
                        required=True,
                        help='Output prefix')
    parser.add_argument('-C',
                        '--leviosam2_index',
                        type=str,
                        required=True,
                        help='Path to the leviosam2 index')
    parser.add_argument('-f',
                        '--target_fasta',
                        type=str,
                        required=True,
                        help='Path to the target reference (FASTA file)')
    parser.add_argument('-fi',
                        '--target_fasta_index',
                        type=str,
                        help=('Path to the target reference index '
                              'for `--aligner`'))
    parser.add_argument('-s',
                        '--source_fasta',
                        type=str,
                        help='Path to the source reference (FASTA file)')
    parser.add_argument('-si',
                        '--source_fasta_index',
                        type=str,
                        help=('Path to the source reference index '
                              'for `--aligner`'))
    parser.add_argument('--dryrun',
                        action='store_true',
                        help='Activate the dryrun mode')
    parser.add_argument('--forcerun',
                        action='store_true',
                        help='Activate the forcerun mode. Rerun everything')
    # parser.add_argument()
    # parser.add_argument()
    # parser.add_argument()
    # parser.add_argument()
    # parser.add_argument()

    args = parser.parse_args()
    return args


class Leviosam2Workflow:
    '''LevioSAM2 workflow module.'''

    @staticmethod
    def validate_binary(cmd: str, lenient: bool = False) -> None:
        '''Validate if an executable is valid.
        
        Args:
            - cmd: command to run
            - lenient: lenient mode.
                If False, return True a returncode of 0. If True, return True
                when either stdout/stderr has >1 lines of output.
                When a command does not exist, we get a "command not found"
                stderr result, so we require >1 lines of output.

        Returns:
            - bool: True if a binary is valid
        '''
        subprocess_out = subprocess.run([cmd], shell=True, capture_output=True)
        if not lenient and subprocess_out.returncode != 0:
            raise ValueError(f'`{cmd}` has a non-zero return code '
                             f'`{subprocess_out.returncode}`')
        else:

            def _count_lines(bin_text):
                return bin_text.decode('utf-8').count('\n')

            if not (_count_lines(subprocess_out.stdout) > 1
                    or _count_lines(subprocess_out.stderr) > 1):
                raise ValueError(f'`{cmd}` has an unexpected output:\n'
                                 '```\n'
                                 f'STDOUT = {subprocess_out.stdout}\n'
                                 f'STDERR = {subprocess_out.stderr}\n'
                                 '```')

    @staticmethod
    def check_input_exists(fn_in: pathlib.Path) -> None:
        if not fn_in.is_file():
            raise FileNotFoundError(f'{fn_in} is not a file')

    def _infer_aligner_binary(self):
        if self.aligner in [
                'bowtie2', 'minimap2', 'winnowmap2', 'strobealign'
        ]:
            self.aligner_binary = self.aligner
        elif self.aligner == 'bwamem':
            self.aligner_binary = 'bwa'
        elif self.aligner == 'bwamem2':
            self.aligner_binary = 'bwa-mem2'
        else:
            raise ValueError(f'Unsupported aligner: {self.aligner}')

    def _validate_binary(self):
        self.validate_binary(cmd=f'{self.samtools_binary} --version')
        self.validate_binary(cmd=f'{self.bgzip_binary} --version')
        if self.measure_time:
            self.validate_binary(cmd=f'{self.gnu_time_binary} --version')
        self.validate_binary(cmd=f'{self.leviosam2_binary}', lenient=True)
        self.validate_binary(cmd=f'{self.aligner_binary}', lenient=True)

    def run_leviosam2(
        self,
        clft: str,
        fn_input: pathlib.Path,
        lift_commit_min_mapq: typing.Union[int, None],
        lift_commit_min_score: typing.Union[int, None],
        lift_commit_max_frac_clipped: typing.Union[float, None],
        lift_commit_max_isize: typing.Union[int, None],
        lift_commit_max_hdist: typing.Union[int, None],
        lift_max_gap: typing.Union[int, None],
        lift_bed_commit_source: str,
        lift_bed_defer_target: str,
        lift_realign_config: str,
    ) -> typing.Union[str, 'subprocess.CompletedProcess[bytes]']:
        '''Run leviosam2.
        '''
        lift_commit_min_mapq_arg = f'-S mapq:{lift_commit_min_mapq}' \
            if lift_commit_min_mapq else ''
        lift_commit_min_score_arg = f'-S aln_score:{lift_commit_min_score}' \
            if lift_commit_min_score else ''
        lift_commit_max_frac_clipped_arg = \
            f'-S clipped_frac:{lift_commit_max_frac_clipped}' \
                if lift_commit_max_frac_clipped else ''
        lift_commit_max_isize_arg = f'-S isize:{lift_commit_max_isize}' \
            if lift_commit_max_isize else ''
        lift_commit_max_hdist_arg = f'-S hdist:{lift_commit_max_hdist}' \
            if lift_commit_max_hdist else ''
        lift_max_gap_arg = f'-G {lift_max_gap}' if lift_max_gap else ''
        lift_bed_commit_source_arg = f'-r {lift_bed_commit_source}' \
            if lift_bed_commit_source else ''
        lift_bed_defer_target_arg = f'-D {lift_bed_defer_target}' \
            if lift_bed_defer_target else ''
        lift_realign_config_arg = f'-x {lift_realign_config}' \
            if lift_realign_config else ''

        fn_out_committed = (self.path_out_prefix.parent /
                            f'{self.path_out_prefix.name}-committed.bam')

        cmd = (f'{self.time_cmd} {self.leviosam2_binary} lift -C {clft} '
               f'-a {fn_input} -p {self.path_out_prefix} '
               f'-t {self.num_threads} -m -f {self.fn_target_fasta} '
               f'{lift_commit_min_mapq_arg} '
               f'{lift_commit_min_score_arg} '
               f'{lift_commit_max_frac_clipped_arg} '
               f'{lift_commit_max_hdist_arg} '
               f'{lift_commit_max_isize_arg} '
               f'{lift_max_gap_arg} '
               f'{lift_bed_commit_source_arg} '
               f'{lift_bed_defer_target_arg} '
               f'{lift_realign_config_arg}')
        if self.dryrun:
            return cmd
        else:
            self.check_input_exists(fn_input)
            if (not self.forcerun) and fn_out_committed.is_file():
                print('[Info] Skip run_leviosam2 -- '
                      f'{fn_out_committed} exists')
                return 'skip'
            return subprocess.run([cmd], shell=True)

    def run_sort_committed(
            self) -> typing.Union[str, 'subprocess.CompletedProcess[bytes]']:
        '''Sort the committed BAM.
        
        Subprocess inputs:
            - <self.path_out_prefix>-committed.bam
        Subprocess outputs:
            - <self.path_out_prefix>-committed-sorted.bam
        '''
        fn_in_bam = (self.path_out_prefix.parent /
                     f'{self.path_out_prefix.name}-committed.bam')
        fn_out = (self.path_out_prefix.parent /
                  f'{self.path_out_prefix.name}-committed-sorted.bam')

        cmd = (
            f'{self.time_cmd} {self.samtools_binary} sort -@ {self.num_threads} '
            f'-o {fn_out} {fn_in_bam}')
        if self.dryrun:
            return cmd
        else:
            self.check_input_exists(fn_in_bam)
            if (not self.forcerun) and fn_out.is_file():
                print('[Info] Skip run_sort_committed -- '
                      f'{fn_out} exists')
                return 'skip'
            return subprocess.run([cmd], shell=True)

    def run_collate_pe(
            self) -> typing.Union[str, 'subprocess.CompletedProcess[bytes]']:
        '''[Paired-end] Collate committed/deferred BAMs to properly paired FASTQs.

        Subprocess inputs:
            - <self.path_out_prefix>-committed-sorted.bam
            - <self.path_out_prefix>-deferred.bam
        Subprocess outputs:
            - <self.path_out_prefix>-paired-deferred-R1.fq.gz
            - <self.path_out_prefix>-paired-deferred-R2.fq.gz
        '''
        fn_in_committed = (self.path_out_prefix.parent /
                           f'{self.path_out_prefix.name}-committed-sorted.bam')
        fn_in_deferred = (self.path_out_prefix.parent /
                          f'{self.path_out_prefix.name}-deferred.bam')
        fn_out_prefix = (self.path_out_prefix.parent /
                         f'{self.path_out_prefix.name}-paired')
        fn_out_fq1 = (self.path_out_prefix.parent /
                      f'{self.path_out_prefix.name}-deferred-R1.fq.gz')
        fn_out_fq2 = (self.path_out_prefix.parent /
                      f'{self.path_out_prefix.name}-deferred-R2.fq.gz')

        cmd = (f'{self.time_cmd} {self.leviosam2_binary} collate '
               f'-a {fn_in_committed} -b {fn_in_deferred} -p {fn_out_prefix}')
        if self.dryrun:
            return cmd
        else:
            self.check_input_exists(fn_in_committed)
            self.check_input_exists(fn_in_deferred)

            if (not self.forcerun
                ) and fn_out_fq1.is_file() and fn_out_fq2.is_file():
                print('[Info] Skip run_collate_pe -- '
                      f'both {fn_out_fq1} and {fn_out_fq2} exist')
                return 'skip'
            return subprocess.run([cmd], shell=True)

    def run_realign_deferred(
        self, target_fasta_index: str, rg_string: str
    ) -> typing.Union[str, 'subprocess.CompletedProcess[bytes]']:
        '''Re-align deferred reads.

        Aligned reads are piped to `samtools sort` for single-end reads.
        Paired-end reads need to be collated later so just compressed.
        Thread resource allocation:
            - paired-end: alignment=`num_threads`-1, view=1
            - single-end: alignment=`num_threads`-sort, sort=`num_threads//5`
        '''

        if not self.is_single_end:
            num_threads_aln = max(1, self.num_threads - 1)
            if self.aligner not in [
                    'bowtie2', 'bwamem', 'bwamem2', 'strobealign'
            ]:
                raise ValueError('We have not supported paired-end '
                                 f'mode for aligner {self.aligner}')
            fn_in_fq1 = (
                self.path_out_prefix.parent /
                f'{self.path_out_prefix.name}-paired-deferred-R1.fq.gz')
            fn_in_fq2 = (
                self.path_out_prefix.parent /
                f'{self.path_out_prefix.name}-paired-deferred-R2.fq.gz')
            fn_out = (self.path_out_prefix.parent /
                      f'{self.path_out_prefix.name}-paired-realigned.bam')
            cmd_samtools = f'{self.time_cmd} {self.samtools_binary} view -hbo {fn_out}'
        else:
            num_threads_sort = max(1, self.num_threads // 5)
            num_threads_aln = max(1, self.num_threads - num_threads_sort)
            fn_in_fq = (self.path_out_prefix.parent /
                        f'{self.path_out_prefix.name}-deferred.fq.gz')
            fn_out = (self.path_out_prefix.parent /
                      f'{self.path_out_prefix.name}-realigned.bam')
            cmd_samtools = (
                f'{self.time_cmd} {self.samtools_binary} sort -@ {num_threads_aln} '
                f'-o {fn_out}')

        if self.aligner == 'bowtie2':
            if not self.is_single_end:
                reads = '-1 {fn_in_fq1} -2 {fn_in_fq2}'
            else:
                reads = '-U {fn_in_fq}'
            cmd = (
                f'{self.time_cmd} {self.aligner_binary} {rg_string} -p {num_threads_aln} '
                f'-x {target_fasta_index} {reads} | '
                f'{cmd_samtools}')
        elif self.aligner in ['bwamem', 'bwamem2']:
            if rg_string != '':
                rg_string = f'-R {rg_string}'
            if not self.is_single_end:
                reads = '{fn_in_fq1} {fn_in_fq2}'
            else:
                reads = '{fn_in_fq}'
            cmd = (f'{self.time_cmd} {self.aligner_binary} mem {rg_string} '
                   f'-t {num_threads_aln} {target_fasta_index} {reads} | '
                   f'{cmd_samtools}')
        elif self.aligner == 'strobealign':
            if rg_string != '':
                rg_string = f'--rg {rg_string}'
            if not self.is_single_end:
                reads = '{fn_in_fq1} {fn_in_fq2}'
            else:
                reads = '{fn_in_fq}'
            cmd = (
                f'{self.time_cmd} {self.aligner_binary} {rg_string} -t {num_threads_aln} '
                f'{self.fn_target_fasta} {reads} | '
                f'{cmd_samtools}')
        elif self.aligner in ['minimap2', 'winnowmap2']:
            # Do not use a prefix other than 'map-hifi' and 'map-ont' modes.
            preset = ''
            if self.sequence_type == 'pb-hifi':
                preset = '-x map-hifi'
            elif self.sequence_type == 'ont':
                preset = '-x map-ont'
            if rg_string != '':
                rg_string = f'-R {rg_string}'
            if not self.is_single_end:
                reads = '{fn_in_fq1} {fn_in_fq2}'
            else:
                reads = '{fn_in_fq}'
            cmd = (
                f'{self.time_cmd} {self.aligner_binary} {rg_string} -a {preset} --MD '
                f'-t {num_threads_aln} {self.fn_target_fasta} {reads} | '
                f'{cmd_samtools}')

        if self.dryrun:
            return cmd
        else:
            self.check_input_exists(fn_in_fq1)
            self.check_input_exists(fn_in_fq2)

            if (not self.forcerun) and fn_out.is_file():
                print(f'[Info] Skip run_realign_deferred -- {fn_out} exists')
                return 'skip'
            return subprocess.run([cmd], shell=True)

    def run_refflow_merge_pe(
        self,
        source_label: str,
        target_label: str,
    ) -> typing.Union[str, 'subprocess.CompletedProcess[bytes]']:
        '''(Paired-end) reference flow-style merging of deferred/realigned BAMs.
        '''
        fn_in_realigned = (self.path_out_prefix.parent /
                           f'{self.path_out_prefix.name}-paired-realigned.bam')
        fn_in_deferred = (self.path_out_prefix.parent /
                          f'{self.path_out_prefix.name}-paired-deferred.bam')
        fn_realigned_sort_n = (
            self.path_out_prefix.parent /
            f'{self.path_out_prefix.name}--paired-realigned-sorted_n.bam')
        fn_deferred_sort_n = (
            self.path_out_prefix.parent /
            f'{self.path_out_prefix.name}--paired-deferred-sorted_n.bam')
        fn_out = (
            self.path_out_prefix.parent /
            f'{self.path_out_prefix.name}-paired-deferred-reconciled-sorted.bam'
        )
        cmd = ''
        cmd += (
            f'{self.time_cmd} {self.samtools_binary} sort -@ {self.num_threads} -n '
            f'-o {fn_realigned_sort_n} {fn_in_realigned} && ')
        cmd += (
            f'{self.time_cmd} {self.samtools_binary} sort -@ {self.num_threads} -n '
            f'-o {fn_deferred_sort_n} {fn_in_deferred} && ')
        cmd += (
            f'{self.time_cmd} {self.leviosam2_binary} reconcile '
            f'-s {source_label}:{fn_deferred_sort_n} '
            f'-s {target_label}:{fn_realigned_sort_n} '
            f'-m -o - | '
            f'{self.time_cmd} {self.samtools_binary} sort -@ {self.num_threads} -o {fn_out}'
        )

        if self.dryrun:
            return cmd
        else:
            self.check_input_exists(fn_in_realigned)
            self.check_input_exists(fn_in_deferred)

            if (not self.forcerun) and fn_out.is_file():
                print(f'[Info] Skip run_refflow_merge_pe -- {fn_out} exists')
                return 'skip'
            return subprocess.run([cmd], shell=True)

    def run_merge_and_index(
        self, ) -> typing.Union[str, 'subprocess.CompletedProcess[bytes]']:
        '''Merge all processed BAMs and index.
        '''
        fn_in_committed = (
            self.path_out_prefix.parent /
            f'{self.path_out_prefix.name}-committed-sorted.bam ')
        if not self.is_single_end:
            fn_in_deferred = (
                self.path_out_prefix.parent /
                f'{self.path_out_prefix.name}-paired-deferred-reconciled-sorted.bam'
            )
        else:
            fn_in_deferred = (self.path_out_prefix.parent /
                              f'{self.path_out_prefix.name}-realigned.bam')
        fn_out = (self.path_out_prefix.parent /
                  f'{self.path_out_prefix.name}-final.bam')

        cmd = ''
        cmd += (
            f'{self.time_cmd} {self.samtools_binary} merge -@ {self.num_threads} --write-index '
            f'-o {fn_out} {fn_in_committed} {fn_in_deferred} && ')
        cmd += (f'{self.time_cmd} {self.samtools_binary} index {fn_out}')

        if self.dryrun:
            return cmd
        else:
            self.check_input_exists(fn_in_committed)
            self.check_input_exists(fn_in_deferred)

            if (not self.forcerun) and fn_out.is_file():
                print(f'[Info] Skip run_merge_and_index -- {fn_out} exists')
                return 'skip'
            return subprocess.run([cmd], shell=True)

    def run_bam_to_fastq_se(
            self) -> typing.Union[str, 'subprocess.CompletedProcess[bytes]']:
        '''(Single-end) Convert deferred BAM to FASTQ.
        '''
        fn_in_bam = (self.path_out_prefix.parent /
                     f'{self.path_out_prefix.name}-deferred.bam')
        fn_out = (self.path_out_prefix.parent /
                  f'{self.path_out_prefix.name}-deferred.fq.gz')
        cmd = (
            f'{self.time_cmd} {self.samtools_binary} fastq index {fn_in_bam} | '
            f'{self.time_cmd} > {fn_out}')

        if self.dryrun:
            return cmd
        else:
            self.check_input_exists(fn_in_bam)

            if (not self.forcerun) and fn_out.is_file():
                print(f'[Info] Skip run_bam_to_fastq_se -- {fn_out} exists')
                return 'skip'
            return subprocess.run([cmd], shell=True)

    def _run_workflow(self):
        # TODO
        # run_intial_align()

        self.run_leviosam2(
            clft=args.leviosam2_index,
            fn_input=fn_input_alignment,
            lift_commit_min_mapq=args.lift_commit_min_mapq,
            lift_commit_min_score=args.lift_commit_min_score,
            lift_commit_max_frac_clipped=args.lift_commit_max_frac_clipped,
            lift_commit_max_isize=args.lift_commit_max_isize,
            lift_commit_max_hdist=args.lift_commit_max_hdist,
            lift_max_gap=args.lift_max_gap,
            lift_bed_commit_source=args.lift_bed_commit_source,
            lift_bed_defer_target=args.lift_bed_defer_target,
            lift_realign_config=args.lift_realign_config,
        )

        self.run_sort_committed()

        if not self.is_single_end:
            self.run_collate_pe()
            self.run_realign_deferred()
            self.run_refflow_merge_pe(
                source_label=args.source_label,
                target_label=args.target_label,
            )
        else:
            self.run_bam_to_fastq_se()

            self.run_realign_deferred()

        self.run_merge_and_index()
        # self.run_clean()

    def __init__(self, args: argparse.Namespace) -> None:
        self.aligner = args.aligner
        self.aligner_binary = args.aligner_binary
        if self.aligner_binary == 'auto':
            self._infer_aligner_binary()
        self.sequence_type = args.sequence_type
        self.is_single_end = (self.sequence_type not in ['ilmn_pe'])
        # self.out_prefix = args.out_prefix
        self.path_out_prefix = pathlib.Path(args.out_prefix)
        self.num_threads = args.num_threads
        self.dryrun = args.dryrun
        self.forcerun = args.forcerun

        # executables
        self.samtools_binary = args.samtools_binary
        self.bgzip_binary = args.bgzip_binary
        # self.gnu_time_binary = args.gnu_time_binary
        self.leviosam2_binary = args.leviosam2_binary

        # Computational performance measurement related
        # self.measure_time = args.measure_time
        self.time_cmd = ''
        if args.measure_time:
            self.time_cmd = (f'{args.gnu_time_binary} -v '
                             f'-ao {self.path_out_prefix}.time_log')

        # Pathify
        # path_out_prefix = pathlib.Path(args.out_prefix)
        self.fn_target_fasta = pathlib.Path(args.target_fasta)
        self.fn_input_alignment = pathlib.Path(args.input_alignment)

        # Check inputs
        self.check_input_exists(self.fn_target_fasta)
        self.check_input_exists(self.fn_input_alignment)

        # Check if executables are valid
        self._validate_binary()

        self._run_workflow()


def run_workflow(args: argparse.Namespace):

    workflow = Leviosam2Workflow(args)

    return 0


if __name__ == '__main__':
    args = parse_args()
    run_workflow(args)
