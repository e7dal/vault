# Secrets view

import time
import random

from sqlalchemy import or_
from tabulate import tabulate
from passwordgenerator import pwgenerator

from ..models.base import get_session
from ..models.Secret import Secret
from ..modules.misc import get_input, confirm
from ..modules.carry import global_scope
from ..views.categories import get_name as get_category_name, pick
from ..views import clipboard


def all():
    """
        Return a list of all secrets
    """

    return get_session().query(Secret).order_by(Secret.id).all()


def to_table(rows=[]):
    """
        Transform rows in a table
    """

    # Retrieve id and name
    all_secrets = [[secret.id, get_category_name(secret.category_id), secret.name,
                    secret.url, secret.login] for secret in rows]

    if len(all_secrets) > 0:
        return tabulate(all_secrets, headers=['Item', 'Category', 'Name', 'URL', 'Login'])
    else:
        return 'Empty!'


def count():
    """
        Return a count of all secrets
    """

    return get_session().query(Secret).count()


def get_by_id(id_):
    """
        Get a secret by ID
    """

    return get_session().query(Secret).get(int(id_))


def add(name, url='', login='', password='', notes='', category_id=None):
    """
        Create a new secret
    """

    secret = Secret(name=name,
                    url=url,
                    login=login,
                    password=password,
                    notes=notes,
                    category_id=category_id)
    get_session().add(secret)
    get_session().commit()

    return True


def add_input():
    """
        Ask user for a secret details and create it
    """

    # Ask user input
    category_id = pick(
        message='* Choose a category number (or leave empty for none): ', optional=True)
    if category_id is False:
        return False

    name = get_input(message='* Name: ')
    if name is False:
        return False

    url = get_input(message='* URL: ')
    if url is False:
        return False

    login = get_input(message='* Login: ')
    if login is False:
        return False

    print('* Password suggestion: %s' % (pwgenerator.generate()))
    password = get_input(message='* Password: ', secure=True)
    if password is False:
        return False

    notes = notes_input()
    if notes is False:
        return False

    # Save item
    add(name=name,
        url=url,
        login=login,
        password=password,
        notes="\n".join(notes),
        category_id=category_id or None)

    print()
    print('The new item has been saved to your vault.')
    print()

    return True


def notes_input():
    """
        Ask user to input notes
    """

    print('* Notes: (press [ENTER] twice to complete)')
    notes = []
    for i in range(15):  # Max 15 lines
        input_ = get_input(message="> ")
        if input_ is False:
            return False

        if input_ == "":
            break
        else:
            notes.append(input_)

    return "\n".join(notes)


def delete(id_):
    """
        Delete a secret
    """

    secret = get_session().query(Secret).filter(Secret.id == int(id_)).first()

    if secret:
        get_session().delete(secret)
        get_session().commit()

        return True

    return False


def delete_confirm(id_):
    """
        Delete a secret (ID is an input, just asking for confirmation)
    """

    if confirm('Confirm deletion?', False):
        result = delete(id_)

        if result is True:
            print()
            print('The secret has been deleted.')

        return result

    return False


def search(query):
    """
        Search by keyword
    """

    query = '%' + str(query) + '%'

    return get_session().query(Secret) \
        .filter(or_(Secret.name.like(query), Secret.url.like(query), Secret.login.like(query))) \
        .order_by(Secret.id).all()


def search_dispatch(query):
    """
        Run a user search. If the query is an integer we will first search by id, otherwise,
        it will be a keyword based search
    """

    if type(query) is int or query.isdigit():
        # Search an ID matching the input
        row = get_by_id(int(query))

        if row:
            return [row]

    # Otherwise return search result
    return search(query)


def search_input():
    """
        Ask user to input a search query
    """

    # Ask user input
    print()
    query = get_input(message='Enter search: ')

    if not query:
        print()
        print('Empty search!')
        return False

    # To prevent fat-finger errors, the search menu will also respond to common commands
    if query in ['s', 'a', 'l', 'q']:  # Common commands
        return query
    elif query == 'b':  # Return to previous menu
        return False

    # Get results
    results = search_dispatch(query)

    if len(results) == 1:  # Exactly one result
        return item_view(results[0])
    elif len(results) > 1:  # More than one result
        return search_results(results)
    else:
        print('No results!')
        return False


def search_results(rows):
    """
        Display search results
    """

    print()
    print(to_table(rows))
    print()

    # Ask user input
    input_ = get_input(
        message='Select a result # or type any key to go back to the main menu: ')

    if input_:
        try:
            result = [row for row in rows if row.id == int(input_)]

            if result:
                return item_view(result[0])
        except ValueError:  # Non integer
            pass

    return False


def item_view(item):
    """
        Show a secret
    """

    print()
    print(to_table([item]))
    print()

    # Show eventual notes
    if item.notes:
        print('Notes:')
        print(item.notes)
        print()

    # Show item menu
    return item_menu(item)


def item_menu(item):
    """
        Item menu
    """

    while True:
        command = get_input(
            message='Choose a command [copy (l)ogin or (p)assword to clipboard / sh(o)w password / (e)dit / (d)elete / (s)earch / (b)ack to Vault]: ',
            lowercase=True,
            # non_locking_values=['l', 'q']
        )

        # Action based on command
        if command == 'l':  # Copy login to the clipboard
            clipboard.copy(item.login, 'login')
            clipboard.wait()
        elif command == 'p':  # Copy a secret to the clipboard
            clipboard.copy(item.password)
            clipboard.wait()
        elif command == 'o':  # Show a secret
            show_secret(item.password)
        elif command == 'e':  # Edit an item
            item_menu_edit(item)
            return
        elif command == 'd':  # Delete an item
            delete_confirm(item.id)
            return
        elif command in ['s', 'b', 'q']:  # Common commands
            return command


def item_menu_edit(item):
    """
        Edit an item
    """

    print()
    command = get_input(
        message='Choose what you would like to edit [(c)ategory / (n)ame  / (u)rl / (l)ogin / (p)assword / n(o)tes / (b)ack to Vault]: ',
        lowercase=True,
        # non_locking_values=['l', 'q']
    )

    # Action based on command
    if command == 'c':  # Edit category
        edit_input('category', item)
        return
    elif command == 'n':  # Edit name
        edit_input('name', item)
        return
    elif command == 'u':  # Edit URL
        edit_input('url', item)
        return
    elif command == 'l':  # Edit login
        edit_input('login', item)
        return
    elif command == 'p':  # Edit password
        edit_input('password', item)
        return
    elif command == 'o':  # Edit notes
        edit_input('notes', item)
        return
    elif command == 'b':  # Back to vault menu
        return

    return


def edit_input(element_name, item):
    """
        Edit an item
    """

    if element_name == 'category':
        print('* Current nategory: %s' %
              (get_category_name(item.category_id) or 'Empty!'))
        category_id = pick(message='* New category: ')

        if category_id is not False:
            item.category_id = category_id
        else:
            print('\nCancelled!')
            return False
    elif element_name == 'name':
        print('* Current name: %s' % (item.name or 'Empty!'))
        name = get_input(message='* New name: ')

        if name is not False:
            item.name = name
        else:
            print('\nCancelled!')
            return False
    elif element_name == 'url':
        print('* Current URL: %s' % (item.url) or 'Empty!')
        url = get_input(message='* New URL: ')

        if url is not False:
            item.url = url
        else:
            print('\nCancelled!')
            return False
    elif element_name == 'login':
        print('* Current login: %s' % (item.login) or 'Empty!')
        login = get_input(message='* New login: ')

        if login is not False:
            item.login = login
        else:
            print('\nCancelled!')
            return False
    elif element_name == 'password':
        print('* Password suggestion: %s' % (pwgenerator.generate()))
        password = get_input(message='* New password: ', secure=True)

        if password is not False:
            item.password = password
        else:
            print('\nCancelled!')
            return False
    elif element_name == 'notes':
        print('* Current notes: %s' % (item.notes) or 'Empty!')
        notes = notes_input()

        if notes is not False:
            item.notes = notes
        else:
            print('\nCancelled!')
            return False
    else:
        raise ValueError('Element `%s` not not exists.' % (element_name))

    # Process update
    get_session().add(item)
    get_session().commit()

    print('The %s has been updated.' % (element_name))

    return True


def show_secret(password):
    """
        Show a secret for X seconds and erase it from the screen
    """

    try:
        print("* The password will be hidden after %s seconds." %
              (global_scope['conf'].hideSecretTTL))
        print('* The password is: %s' % (password), end="\r")

        time.sleep(int(global_scope['conf'].hideSecretTTL))
    except KeyboardInterrupt:
        # Will catch `^-c` and immediately hide the password
        pass

    print('* The password is: ' + '*' * (len(password) + random.randint(1, 8)))

    return True
