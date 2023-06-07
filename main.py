# Load the API
from inaSpeechSegmenter import Segmenter
from inaSpeechSegmenter.export_funcs import seg2csv, seg2textgrid
import subprocess, os, glob
# select a media to analyse
# any media supported by ffmpeg may be used (video, audio, urls)
import json
import sys
def segment(media, batch_size = 32):
    seg = Segmenter(vad_engine='sm', detect_gender=False, energy_ratio = 0.02, batch_size = batch_size)
    segmentation = seg(media)
    return segmentation
def extract_music(segmentation, segment_thres = 60, segment_thres_final = 90, 
                  segment_connect = 5, start_padding = 1, end_padding = 2):
    r = []
    #bridges noEnergy segments that are likely fragmented
    for i in range(len(segmentation)-2, 0, -1):
        if segmentation[i][0] == 'noEnergy' and segmentation[i][2] - segmentation[i][1] < 2 and \
        segmentation[i-1][0] == segmentation[i+1][0]:
            segmentation[i-1] = (segmentation[i-1][0], segmentation[i-1][1], segmentation[i+1][2])
    for i in segmentation: 
        if i[0] == 'music' and i[2]-i[1] > segment_thres: r.append(['',i[1] - start_padding, i[2] + end_padding])    
    for i in range(len(r)-1, 0, -1):
        if r[i][1] - r[i-1][2] < segment_connect:
            r[i-1][2] = r[i][2]
            r[i][1] = r[i][2] + 1    
    rf = []
    for i in r:
        if i[2]-i[1] > segment_thres_final: rf.append(i)
    return [['{}:{}:{}'.format(str(int(x[1]//3600)), 
                               str(int(x[1] % 3600 //60)), 
                               str(int(x[1] % 60)).zfill(2)), 
             '{}:{}:{}'.format(str(int(x[2]//3600)), 
                               str(int(x[2]  % 3600  //60)), 
                               str(int(x[2] % 60)).zfill(2))] for x in rf]
def extract_mah_stuff(media, segmented_stamps, outdir = None):
    timestamps = []
    nameswitch = False
    try:
        for i in open(r"timestamp.ini", 'r', encoding='UTF-8'):
            i = i.replace('\n','').replace('」', '').replace('~「',' ').replace('「', ' ').replace('『', ' ').replace('』', ' ')
            if ':' in i:
                timestamps.append([i[:i.find(' ')], i[i.find(' ')+1:]])
                #timestamps[-1][1] = timestamps[-1][1][1:]
                timestamps[-1][1] = timestamps[-1][1].replace('/', 'by')
                #timestamps[-1][1] = timestamps[-1][1].replace('-', 'by')
                while timestamps[-1][1][0] == ' ': timestamps[-1][1] = timestamps[-1][1][1:]
                while timestamps[-1][1][-1] == ' ': timestamps[-1][1] = timestamps[-1][1][:-1]
        #        nameswitch = True
            elif nameswitch:
                nameswitch = False
                timestamps[-1].append(i)
        with open(r"timestamp.ini", 'w') as f:
            pass
    except:
        pass
    print('timestamp assist', timestamps)
    timestamps_ext = segmented_stamps#extract_music(segmentation)#[['{}:{}:{}'.format(str(int(x[1]//3600)), str(int(x[1] % 3600 //60)), str(int(x[1] % 60)).zfill(2)),  '{}:{}:{}'.format(str(int(x[2]//3600)), str(int(x[2]  % 3600  //60)), str(int(x[2] % 60)).zfill(2))] for x in r]
    nameswitch = False
    file = media
    filename = file[:file.rfind('.')]
    fileext = file[len(filename):]
    filename = os.path.basename(filename)
    if not os.path.exists(outdir):
        os.makedirs(outdir)
    for i in range(len(timestamps_ext)):
        oud = outdir if outdir else os.path.dirname(file)
        # try:
        #     pass
        #     prefix = timestamps[i][1]
        #     subprocess.call('ffmpeg -i "{}" {} -c:v copy -c:a copy "{}"'.format(
        #     file, 
        #     '-ss {} -to {}'.format(timestamps[i][0], timestamps_ext[i][1],),
        #     os.path.join(oud, filename + '-' + prefix + fileext)))
        # except:
        #     prefix = str(i)
        #     subprocess.call('ffmpeg -i "{}" {} -c:v copy -c:a copy "{}"'.format(
        #         file, 
        #         '-ss {} -to {}'.format(timestamps_ext[i][0], timestamps_ext[i][1],),
        #         os.path.join(oud, filename + '-' + prefix + fileext)))
        prefix = str(i)
        os.system('ffmpeg -i "{}" {} -c:v copy -c:a copy "{}"'.format(
            file, 
            '-ss {} -to {}'.format(timestamps_ext[i][0], timestamps_ext[i][1],),
            os.path.join(oud, filename + '-' + prefix + fileext)))

from ShazamAPI import Shazam
import time, json
def shazam(mp3, stop_at_first_match = True, force_sleep = 5):
    mp3_file_content_to_recognize = open(mp3, 'rb').read()
    shazam = Shazam(mp3_file_content_to_recognize)
    recognize_generator = shazam.recognizeSong()
    matches = []
    try:
        while True:
            match = next(recognize_generator)
            if len(match[1]['matches']) > 0: 
                matches.append(match)
                if stop_at_first_match: raise StopIteration()
    except StopIteration:
        pass
    return matches

def legalize_filename(fn):
    return fn.replace(':', ' ').replace('"', '').replace(r'/', '').replace(r'?', '')

def shazam_title(match):
    return [
    legalize_filename(match[1]['track']['title']),
    legalize_filename(match[1]['track']['subtitle']),    
    ]
results = {}

def main(media, outdir):
    extract_mah_stuff(media, extract_music(segment(media)), outdir)

    f = open(f'log/{outdir}.txt', 'w')
    for file in glob.glob(outdir + '/*'):
        filename = file[:file.rfind('.')]
        fileext = file[len(filename):]
        fn = os.path.basename(filename)
        if fn in results and results[fn] != None: print(fn, results[fn], 'loaded')
        elif not fn in results:
            print('shazaming', fn)
            try:
                results[fn] = shazam_title(shazam(file)[0])
                print(fn, 'shazam found to be', results[fn])
                f.write(f'{fn} shazam found to be {results[fn]}\n')
                os.rename(file, 
                    os.path.join(
                    # os.path.dirname(file),
                    (filename + "-{}".format(results[fn][0].replace(':', ' '))) + fileext
                    ))            
            except IndexError:
                print(fn, 'shazam failed')
                results[fn] = None
    f.close()

def menu():
    while True:
        try:
            media = input('请输入录播地址：')
            outdir = input('请输入输出文件夹: ')
            main(media, outdir)
            print('任务完成')
        except Exception as e:
            print(type(e), e)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])