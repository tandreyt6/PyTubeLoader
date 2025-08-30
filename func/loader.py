import os
import multiprocessing as mp
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

def _info_worker(index, url, q):
    try:
        import yt_dlp
        ydl_opts = {'quiet': True, 'no_warnings': True, 'noplaylist': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        q.put(('info_ok', index, {'info': info}))
    except Exception as e:
        q.put(('info_err', index, {'message': str(e)}))

def _download_worker(index, url, out_dir, proxy, q, filename):
    try:
        import yt_dlp
        def hook(d):
            payload = {
                'status': d.get('status'),
                'downloaded_bytes': d.get('downloaded_bytes'),
                'total_bytes': d.get('total_bytes'),
                'total_bytes_estimate': d.get('total_bytes_estimate'),
                'speed': d.get('speed'),
                'eta': d.get('eta'),
                'filename': d.get('filename'),
            }
            q.put(('progress', index, payload))
        ydl_opts = {
            'outtmpl': os.path.join(out_dir, filename),
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'webm',
            'noplaylist': True,
            'progress_hooks': [hook],
            'quiet': True,
            'no_warnings': False,
        }
        if proxy:
            print(proxy)
            ydl_opts['proxy'] = proxy
        q.put(('status', index, {'text': 'Начало загрузки'}))
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        q.put(('done', index, {'ok': True, 'message': 'Загрузка завершена'}))
    except Exception as e:
        q.put(('done', index, {'ok': False, 'message': str(e)}))

class DownloadManager(QObject):
    info_received   = pyqtSignal(int, dict)
    info_error      = pyqtSignal(int, str)
    progress_changed= pyqtSignal(int, float)
    status_changed  = pyqtSignal(int, str)
    finished_signal = pyqtSignal(int, bool, str)

    def __init__(self, out_dir='.', proxy=None, poll_interval_ms=80):
        super().__init__()
        self.queue = []
        self.out_dir = out_dir
        self.proxy = proxy
        self._mp_queue = mp.Queue()
        self._info_procs = {}
        self._download_procs = {}
        self._timer = QTimer()
        self._timer.timeout.connect(self._poll_queue)
        self._timer.start(poll_interval_ms)

    def add_video(self, url):
        item = {'url': url, 'status': 'queued', 'title': None, 'filepath': None}
        existing_index = None
        for i, existing_item in enumerate(self.queue):
            if existing_item['url'] == url:
                existing_index = i
                break
        if existing_index is not None:
            return 0, existing_index
        self.queue.append(item)
        return 1, len(self.queue) - 1

    def get_info(self, index):
        if not (0 <= index < len(self.queue)):
            raise IndexError("Индекс вне диапазона очереди")
        if index in self._info_procs:
            return
        url = self.queue[index]['url']
        p = mp.Process(target=_info_worker, args=(index, url, self._mp_queue), daemon=True)
        p.start()
        self._info_procs[index] = p

    def start_download(self, index):
        if not (0 <= index < len(self.queue)):
            raise IndexError("Индекс вне диапазона очереди")
        if index in self._download_procs:
            return
        url = self.queue[index]['url']
        p = mp.Process(target=_download_worker, args=(index, url, self.out_dir, self.proxy, self._mp_queue, self.queue[index].get('_filename')), daemon=True)
        p.start()
        self._download_procs[index] = p
        self.queue[index]['status'] = 'downloading'
        self.status_changed.emit(index, "Запущено")

    def stop_download(self, index):
        p = self._download_procs.get(index)
        if p and p.is_alive():
            try:
                p.terminate()
            except Exception:
                pass
            finally:
                p.join(timeout=1.0)
                self._download_procs.pop(index, None)
                self.queue[index]['status'] = 'stopped'
                self.status_changed.emit(index, "Остановлен")
                self.finished_signal.emit(index, False, "Остановлено пользователем")

    def _poll_queue(self):
        try:
            while True:
                kind, index, data = self._mp_queue.get_nowait()
                if kind == 'info_ok':
                    info = data['info']
                    self.queue[index]['title'] = info.get('title', 'Без названия')
                    self.info_received.emit(index, info)
                    self._cleanup_info_proc(index)
                elif kind == 'info_err':
                    self.info_error.emit(index, data.get('message', 'Ошибка'))
                    self._cleanup_info_proc(index)
                elif kind == 'status':
                    self.status_changed.emit(index, data.get('text', ''))
                elif kind == 'progress':
                    st = data.get('status')
                    if st == 'downloading':
                        total = data.get('total_bytes') or data.get('total_bytes_estimate') or 0
                        downloaded = data.get('downloaded_bytes') or 0
                        percent = (downloaded / total * 100) if total else 0.0
                        self.progress_changed.emit(index, percent)
                        self.status_changed.emit(index, f"Загружено: {percent:.2f}%")
                    elif st == 'finished':
                        fn = data.get('filename')
                        self.progress_changed.emit(index, 100.0)
                        self.status_changed.emit(index, f"Файл готов: {fn}" if fn else "Файл готов")
                elif kind == 'done':
                    ok = bool(data.get('ok'))
                    msg = data.get('message', '')
                    self._cleanup_download_proc(index)
                    if not ok and self.queue[index].get('status') == 'stopped':
                        continue
                    self.finished_signal.emit(index, ok, msg)
        except Exception:
            pass

    def _cleanup_info_proc(self, index):
        p = self._info_procs.pop(index, None)
        if p:
            try:
                if p.is_alive():
                    p.join(timeout=0.5)
            except Exception:
                pass

    def _cleanup_download_proc(self, index):
        p = self._download_procs.pop(index, None)
        if p:
            try:
                if p.is_alive():
                    p.join(timeout=0.5)
            except Exception:
                pass
