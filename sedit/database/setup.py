import zipfile

def extractDB():
	print "extracting database..."
	zfile = zipfile.ZipFile('db.zip')
	zfile.extractall()
	print "database extracted"


if __name__ == '__main__':
	extractDB()
