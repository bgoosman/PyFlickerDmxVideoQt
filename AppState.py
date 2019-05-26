class AppState:
    def __init__(self, qApplication):
        self.threads = []
        self.qtApplication = qApplication

    def addThread(self, thread):
        self.threads.append(thread)

    def quit(self):
        for t in self.threads:
            t.join()
        self.qtApplication.exit()
