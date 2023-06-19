FROM ubuntu:22.04

RUN apt-get update
RUN apt-get upgrade -y
RUN apt-get install -y --fix-missing python3 python3-pip
RUN pip3 install discord asyncio
RUN useradd -d /home/hogrida -m -p royalhogs -s /bin/bash hogrida

WORKDIR /home/hogrida

ADD bot.py /home/hogrida/
ADD mail.json /home/hogrida/
ADD serverdb.json /home/hogrida/
ADD token.txt /home/hogrida/

RUN chmod 555 /home/hogrida/bot.py
RUN chmod 440 /home/hogrida/mail.json
RUN chmod 440 /home/hogrida/serverdb.json
RUN chmod 440 /home/hogrida/token.txt

RUN chown root:hogrida /home/hogrida/bot.py
RUN chown root:hogrida /home/hogrida/mail.json
RUN chown root:hogrida /home/hogrida/serverdb.json
RUN chown root:hogrida /home/hogrida/token.txt

USER hogrida

CMD /bin/bash -c ./bot.py
