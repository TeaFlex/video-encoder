<#
.SYNOPSIS
    Encodes a video file using FFmpeg with NVIDIA NVENC hardware acceleration.
.DESCRIPTION
    This script takes an input video file and encodes it to H.264 using NVIDIA NVENC,
    copying audio and subtitle tracks as-is.
.PARAMETER InputPath
    The path to the input video file.
.EXAMPLE
    .\Encode-Video.ps1 -InputPath "C:\Videos\input.mkv"
#>

param (
    [Parameter(Mandatory=$true)]
    [string]$InputPath
)

# Get the directory and filename without extension
$InputFile = Get-Item -Path $InputPath
$OutputDir = $InputFile.DirectoryName
$InputName = $InputFile.BaseName
$OutputPath = Join-Path -Path $OutputDir -ChildPath "${InputName}_encoded.mkv"

Write-Host "Encoding $InputPath to $OutputPath..."

# FFmpeg command using NVIDIA NVENC
$ffmpegCommand = @(
    "ffmpeg",
    "-hwaccel", "cuda", 
    "-hwaccel_output_format", "cuda",
    "-i", $InputPath,
    "-c:v", "hevc_nvenc",
    "-preset", "p6", 
    "-profile:v", "main10",  
    "-rc", "constqp",
    "-cq", "22",
    "-b:v", "0",
    "-map", "0:v",
    "-map", "0:a",
    "-map", "0:s?",
    "-c:a", "aac",
    "-b:a", "192k",
    "-c:s", "copy",
    $OutputPath
)

# Join the command array into a string
$commandString = $ffmpegCommand -join " "

# Execute the command
Invoke-Expression $commandString

if ($LASTEXITCODE -eq 0) {
    Write-Host "Encoding completed successfully!"
} else {
    Write-Host "Encoding failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}
