DESTDIR ?= /usr

.PHONY: install
install: testrunner.1
	test -f ${DESTDIR}/bin/ || mkdir -p ${DESTDIR}/bin/
	test -f ${DESTDIR}/share/man/man1/ || mkdir -p ${DESTDIR}/share/man/man1/
	install -m 0755 testrunner.py ${DESTDIR}/bin/
	install -m 0755 testrunner.1 ${DESTDIR}/man/man1/

testrunner.1: README
	a2x -f manpage README

.PHONY: clean
clean:
	rm -f testrunner.1
