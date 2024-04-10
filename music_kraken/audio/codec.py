from pathlib import Path
from typing import List, Tuple
from tqdm import tqdm
from ffmpeg_progress_yield import FfmpegProgress

from ..utils.config import main_settings, logging_settings
from ..objects import Target


LOGGER = logging_settings["codex_logger"]


def correct_codec(target: Target, bitrate_kb: int = main_settings["bitrate"], audio_format: str = main_settings["audio_format"], interval_list: List[Tuple[float, float]] = None):
    if not target.exists:
        LOGGER.warning(f"Target doesn't exist: {target.file_path}")
        return
    
    interval_list = interval_list or []

    bitrate_b = int(bitrate_kb / 1024)

    output_target = Target(
        file_path=Path(str(target.file_path) + "." + audio_format)
    )
    
    # get the select thingie
    # https://stackoverflow.com/questions/50594412/cut-multiple-parts-of-a-video-with-ffmpeg
    aselect_list: List[str] = []
    
    start = 0
    next_start = 0
    for end, next_start in interval_list:
        aselect_list.append(f"between(t,{start},{end})")
        start = next_start
    aselect_list.append(f"gte(t,{next_start})")
    
    select = f"aselect='{'+'.join(aselect_list)}',asetpts=N/SR/TB"
    
    # build the ffmpeg command
    ffmpeg_command = [
        str(main_settings["ffmpeg_binary"]), 
        "-i", str(target.file_path), 
        "-af", select, 
        "-b", str(bitrate_b),
        str(output_target.file_path)
    ]

    # run the ffmpeg command with a progressbar
    ff = FfmpegProgress(ffmpeg_command)
    with tqdm(total=100, desc=f"removing {len(interval_list)} segments") as pbar:
        for progress in ff.run_command_with_progress():
            pbar.update(progress-pbar.n)

    LOGGER.debug(ff.stderr)

    output_target.copy_content(target)
    output_target.delete()
