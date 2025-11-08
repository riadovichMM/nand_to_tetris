filename = input("input filename without: ")

my_file = open('./my/my_' + filename, 'r')
their_file = open('./their/' + filename, 'r')

loop = True

while loop:
    my_line = my_file.readline()
    their_line = their_file.readline()

    if my_line != their_line:
        loop = False
        print('Error')


    if my_file == '' or their_line == '':
        loop = False
        print('All Good!')

