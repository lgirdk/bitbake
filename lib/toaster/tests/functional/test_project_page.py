#! /usr/bin/env python3 #
# BitBake Toaster UI tests implementation
#
# Copyright (C) 2023 Savoir-faire Linux
#
# SPDX-License-Identifier: GPL-2.0-only
#

import pytest
from time import sleep
from django.urls import reverse
from django.utils import timezone
from selenium.webdriver.support.select import Select
from selenium.common.exceptions import NoSuchElementException
from tests.functional.functional_helpers import SeleniumFunctionalTestCase
from orm.models import Build, Project, Target
from selenium.webdriver.common.by import By


@pytest.mark.django_db
class TestProjectPage(SeleniumFunctionalTestCase):

    def setUp(self):
        super().setUp()
        release = '3'
        project_name = 'projectmaster'
        self._create_test_new_project(
            project_name,
            release,
            False,
        )

    def _create_test_new_project(
        self,
        project_name,
        release,
        merge_toaster_settings,
    ):
        """ Create/Test new project using:
          - Project Name: Any string
          - Release: Any string
          - Merge Toaster settings: True or False
        """
        self.get(reverse('newproject'))
        self.driver.find_element(By.ID,
                                 "new-project-name").send_keys(project_name)

        select = Select(self.find('#projectversion'))
        select.select_by_value(release)

        # check merge toaster settings
        checkbox = self.find('.checkbox-mergeattr')
        if merge_toaster_settings:
            if not checkbox.is_selected():
                checkbox.click()
        else:
            if checkbox.is_selected():
                checkbox.click()

        self.driver.find_element(By.ID, "create-project-button").click()

    def _get_create_builds(self, **kwargs):
        """ Create a build and return the build object """
        # parameters for builds to associate with the projects
        now = timezone.now()
        release = '3'
        project_name = 'projectmaster'
        self._create_test_new_project(
            project_name+"2",
            release,
            False,
        )

        self.project1_build_success = {
            'project': Project.objects.get(id=1),
            'started_on': now,
            'completed_on': now,
            'outcome': Build.SUCCEEDED
        }

        self.project1_build_failure = {
            'project': Project.objects.get(id=1),
            'started_on': now,
            'completed_on': now,
            'outcome': Build.FAILED
        }
        build1 = Build.objects.create(**self.project1_build_success)
        build2 = Build.objects.create(**self.project1_build_failure)

        # add some targets to these builds so they have recipe links
        # (and so we can find the row in the ToasterTable corresponding to
        # a particular build)
        Target.objects.create(build=build1, target='foo')
        Target.objects.create(build=build2, target='bar')

        if kwargs:
            # Create kwargs.get('success') builds with success status with target
            # and kwargs.get('failure') builds with failure status with target
            for i in range(kwargs.get('success', 0)):
                now = timezone.now()
                self.project1_build_success['started_on'] = now
                self.project1_build_success[
                    'completed_on'] = now - timezone.timedelta(days=i)
                build = Build.objects.create(**self.project1_build_success)
                Target.objects.create(build=build,
                                      target=f'{i}_success_recipe',
                                      task=f'{i}_success_task')

            for i in range(kwargs.get('failure', 0)):
                now = timezone.now()
                self.project1_build_failure['started_on'] = now
                self.project1_build_failure[
                    'completed_on'] = now - timezone.timedelta(days=i)
                build = Build.objects.create(**self.project1_build_failure)
                Target.objects.create(build=build,
                                      target=f'{i}_fail_recipe',
                                      task=f'{i}_fail_task')
        return build1, build2

    def _mixin_test_table_edit_column(
            self,
            table_id,
            edit_btn_id,
            list_check_box_id: list
    ):
        # Check edit column
        edit_column = self.find(f'#{edit_btn_id}')
        self.assertTrue(edit_column.is_displayed())
        edit_column.click()
        # Check dropdown is visible
        self.wait_until_visible('ul.dropdown-menu.editcol')
        for check_box_id in list_check_box_id:
            # Check that we can hide/show table column
            check_box = self.find(f'#{check_box_id}')
            th_class = str(check_box_id).replace('checkbox-', '')
            if check_box.is_selected():
                # check if column is visible in table
                self.assertTrue(
                    self.find(
                        f'#{table_id} thead th.{th_class}'
                    ).is_displayed(),
                    f"The {th_class} column is checked in EditColumn dropdown, but it's not visible in table"
                )
                check_box.click()
                # check if column is hidden in table
                self.assertFalse(
                    self.find(
                        f'#{table_id} thead th.{th_class}'
                    ).is_displayed(),
                    f"The {th_class} column is unchecked in EditColumn dropdown, but it's visible in table"
                )
            else:
                # check if column is hidden in table
                self.assertFalse(
                    self.find(
                        f'#{table_id} thead th.{th_class}'
                    ).is_displayed(),
                    f"The {th_class} column is unchecked in EditColumn dropdown, but it's visible in table"
                )
                check_box.click()
                # check if column is visible in table
                self.assertTrue(
                    self.find(
                        f'#{table_id} thead th.{th_class}'
                    ).is_displayed(),
                    f"The {th_class} column is checked in EditColumn dropdown, but it's not visible in table"
                )

    def _get_config_nav_item(self, index):
        config_nav = self.find('#config-nav')
        return config_nav.find_elements(By.TAG_NAME, 'li')[index]

    def _navigate_to_config_nav(self, nav_id, nav_index):
        # navigate to the project page
        url = reverse("project", args=(1,))
        self.get(url)
        self.wait_until_visible('#config-nav')
        # click on "Software recipe" tab
        soft_recipe = self._get_config_nav_item(nav_index)
        soft_recipe.click()
        self.wait_until_visible(f'#{nav_id}')

    def _mixin_test_table_show_rows(self, table_selector, **kwargs):
        """ Test the show rows feature in the builds table on the all builds page """
        def test_show_rows(row_to_show, show_row_link):
            # Check that we can show rows == row_to_show
            show_row_link.select_by_value(str(row_to_show))
            self.wait_until_visible(f'#{table_selector} tbody tr', poll=2)
            self.assertTrue(
                len(self.find_all(f'#{table_selector} tbody tr')) == row_to_show
            )
        self.wait_until_present(f'#{table_selector} tbody tr')
        show_rows = self.driver.find_elements(
            By.XPATH,
            f'//select[@class="form-control pagesize-{table_selector}"]'
        )
        rows_to_show = [10, 25, 50, 100, 150]
        to_skip = kwargs.get('to_skip', [])
        # Check show rows
        for show_row_link in show_rows:
            show_row_link = Select(show_row_link)
            for row_to_show in rows_to_show:
                if row_to_show not in to_skip:
                    test_show_rows(row_to_show, show_row_link)

    def _wait_until_build(self, state):
        while True:
            try:
                last_build_state = self.driver.find_element(
                    By.XPATH,
                    '//*[@id="latest-builds"]/div[1]//div[@class="build-state"]',
                )
                build_state = last_build_state.get_attribute(
                    'data-build-state')
                state_text = state.lower().split()
                if any(x in str(build_state).lower() for x in state_text):
                    break
            except NoSuchElementException:
                continue
            sleep(1)

    def _mixin_test_table_search_input(self, **kwargs):
        input_selector, input_text, searchBtn_selector, table_selector, *_ = kwargs.values()
        # Test search input
        self.wait_until_visible(f'#{input_selector}')
        recipe_input = self.find(f'#{input_selector}')
        recipe_input.send_keys(input_text)
        self.find(f'#{searchBtn_selector}').click()
        self.wait_until_visible(f'#{table_selector} tbody tr')
        rows = self.find_all(f'#{table_selector} tbody tr')
        self.assertTrue(len(rows) > 0)

    def test_image_recipe_editColumn(self):
        """ Test the edit column feature in image recipe table on project page """
        self._get_create_builds(success=10, failure=10)

        url = reverse('projectimagerecipes', args=(1,))
        self.get(url)
        self.wait_until_present('#imagerecipestable tbody tr')

        column_list = [
            'get_description_or_summary', 'layer_version__get_vcs_reference',
            'layer_version__layer__name', 'license', 'recipe-file', 'section',
            'version'
        ]

        # Check that we can hide the edit column
        self._mixin_test_table_edit_column(
            'imagerecipestable',
            'edit-columns-button',
            [f'checkbox-{column}' for column in column_list]
        )

    def test_page_header_on_project_page(self):
        """ Check page header in project page:
          - AT LEFT -> Logo of Yocto project, displayed, clickable
          - "Toaster"+" Information icon", displayed, clickable
          - "Server Icon" + "All builds", displayed, clickable
          - "Directory Icon" + "All projects", displayed, clickable
          - "Book Icon" + "Documentation", displayed, clickable
          - AT RIGHT -> button "New project", displayed, clickable
        """
        # navigate to the project page
        url = reverse("project", args=(1,))
        self.get(url)

        # check page header
        # AT LEFT -> Logo of Yocto project
        logo = self.driver.find_element(
            By.XPATH,
            "//div[@class='toaster-navbar-brand']",
        )
        logo_img = logo.find_element(By.TAG_NAME, 'img')
        self.assertTrue(logo_img.is_displayed(),
                        'Logo of Yocto project not found')
        self.assertTrue(
            '/static/img/logo.png' in str(logo_img.get_attribute('src')),
            'Logo of Yocto project not found'
        )
        # "Toaster"+" Information icon", clickable
        toaster = self.driver.find_element(
            By.XPATH,
            "//div[@class='toaster-navbar-brand']//a[@class='brand']",
        )
        self.assertTrue(toaster.is_displayed(), 'Toaster not found')
        self.assertTrue(toaster.text == 'Toaster')
        info_sign = self.find('.glyphicon-info-sign')
        self.assertTrue(info_sign.is_displayed())

        # "Server Icon" + "All builds"
        all_builds = self.find('#navbar-all-builds')
        all_builds_link = all_builds.find_element(By.TAG_NAME, 'a')
        self.assertTrue("All builds" in all_builds_link.text)
        self.assertTrue(
            '/toastergui/builds/' in str(all_builds_link.get_attribute('href'))
        )
        server_icon = all_builds.find_element(By.TAG_NAME, 'i')
        self.assertTrue(
            server_icon.get_attribute('class') == 'glyphicon glyphicon-tasks'
        )
        self.assertTrue(server_icon.is_displayed())

        # "Directory Icon" + "All projects"
        all_projects = self.find('#navbar-all-projects')
        all_projects_link = all_projects.find_element(By.TAG_NAME, 'a')
        self.assertTrue("All projects" in all_projects_link.text)
        self.assertTrue(
            '/toastergui/projects/' in str(all_projects_link.get_attribute(
                'href'))
        )
        dir_icon = all_projects.find_element(By.TAG_NAME, 'i')
        self.assertTrue(
            dir_icon.get_attribute('class') == 'icon-folder-open'
        )
        self.assertTrue(dir_icon.is_displayed())

        # "Book Icon" + "Documentation"
        toaster_docs_link = self.find('#navbar-docs')
        toaster_docs_link_link = toaster_docs_link.find_element(By.TAG_NAME,
                                                                'a')
        self.assertTrue("Documentation" in toaster_docs_link_link.text)
        self.assertTrue(
            toaster_docs_link_link.get_attribute('href') == 'http://docs.yoctoproject.org/toaster-manual/index.html#toaster-user-manual'
        )
        book_icon = toaster_docs_link.find_element(By.TAG_NAME, 'i')
        self.assertTrue(
            book_icon.get_attribute('class') == 'glyphicon glyphicon-book'
        )
        self.assertTrue(book_icon.is_displayed())

        # AT RIGHT -> button "New project"
        new_project_button = self.find('#new-project-button')
        self.assertTrue(new_project_button.is_displayed())
        self.assertTrue(new_project_button.text == 'New project')
        new_project_button.click()
        self.assertTrue(
            '/toastergui/newproject/' in str(self.driver.current_url)
        )

    def test_edit_project_name(self):
        """ Test edit project name:
          - Click on "Edit" icon button
          - Change project name
          - Click on "Save" button
          - Check project name is changed
        """
        # navigate to the project page
        url = reverse("project", args=(1,))
        self.get(url)

        # click on "Edit" icon button
        self.wait_until_visible('#project-name-container')
        edit_button = self.find('#project-change-form-toggle')
        edit_button.click()
        project_name_input = self.find('#project-name-change-input')
        self.assertTrue(project_name_input.is_displayed())
        project_name_input.clear()
        project_name_input.send_keys('New Name')
        self.find('#project-name-change-btn').click()

        # check project name is changed
        self.wait_until_visible('#project-name-container')
        self.assertTrue(
            'New Name' in str(self.find('#project-name-container').text)
        )

    def test_project_page_tabs(self):
        """ Test project tabs:
          - "configuration" tab
          - "Builds" tab
          - "Import layers" tab
          - "New custom image" tab
          Check search box used to build recipes
        """
        # navigate to the project page
        url = reverse("project", args=(1,))
        self.get(url)

        # check "configuration" tab
        self.wait_until_visible('#topbar-configuration-tab')
        config_tab = self.find('#topbar-configuration-tab')
        self.assertTrue(config_tab.get_attribute('class') == 'active')
        self.assertTrue('Configuration' in config_tab.text)
        config_tab_link = config_tab.find_element(By.TAG_NAME, 'a')
        self.assertTrue(
            f"/toastergui/project/1" in str(config_tab_link.get_attribute(
                'href'))
        )

        def get_tabs():
            # tabs links list
            return self.driver.find_elements(
                By.XPATH,
                '//div[@id="project-topbar"]//li'
            )

        def check_tab_link(tab_index, tab_name, url):
            tab = get_tabs()[tab_index]
            tab_link = tab.find_element(By.TAG_NAME, 'a')
            self.assertTrue(url in tab_link.get_attribute('href'))
            self.assertTrue(tab_name in tab_link.text)
            self.assertTrue(tab.get_attribute('class') == 'active')

        # check "Builds" tab
        builds_tab = get_tabs()[1]
        builds_tab.find_element(By.TAG_NAME, 'a').click()
        check_tab_link(
            1,
            'Builds',
            f"/toastergui/project/1/builds"
        )

        # check "Import layers" tab
        import_layers_tab = get_tabs()[2]
        import_layers_tab.find_element(By.TAG_NAME, 'a').click()
        check_tab_link(
            2,
            'Import layer',
            f"/toastergui/project/1/importlayer"
        )

        # check "New custom image" tab
        new_custom_image_tab = get_tabs()[3]
        new_custom_image_tab.find_element(By.TAG_NAME, 'a').click()
        check_tab_link(
            3,
            'New custom image',
            f"/toastergui/project/1/newcustomimage"
        )

        # check search box can be use to build recipes
        search_box = self.find('#build-input')
        search_box.send_keys('core-image-minimal')
        self.find('#build-button').click()
        self.wait_until_visible('#latest-builds')
        lastest_builds = self.driver.find_elements(
            By.XPATH,
            '//div[@id="latest-builds"]',
        )
        last_build = lastest_builds[0]
        self.assertTrue(
            'core-image-minimal' in str(last_build.text)
        )

    def test_softwareRecipe_page(self):
        """ Test software recipe page
            - Check title "Compatible software recipes" is displayed
            - Check search input
            - Check "build recipe" button works
            - Check software recipe table feature(show/hide column, pagination)
        """
        self._navigate_to_config_nav('softwarerecipestable', 4)
        # check title "Compatible software recipes" is displayed
        self.assertTrue("Compatible software recipes" in self.get_page_source())
        # Test search input
        self._mixin_test_table_search_input(
            input_selector='search-input-softwarerecipestable',
            input_text='busybox',
            searchBtn_selector='search-submit-softwarerecipestable',
            table_selector='softwarerecipestable'
        )
        # check "build recipe" button works
        rows = self.find_all('#softwarerecipestable tbody tr')
        image_to_build = rows[0]
        build_btn = image_to_build.find_element(
            By.XPATH,
            '//td[@class="add-del-layers"]'
        )
        build_btn.click()
        self._wait_until_build('parsing starting cloning')
        lastest_builds = self.driver.find_elements(
            By.XPATH,
            '//div[@id="latest-builds"]/div'
        )
        self.assertTrue(len(lastest_builds) > 0)

        # check software recipe table feature(show/hide column, pagination)
        self._navigate_to_config_nav('softwarerecipestable', 4)
        column_list = [
            'get_description_or_summary',
            'layer_version__get_vcs_reference',
            'layer_version__layer__name',
            'license',
            'recipe-file',
            'section',
            'version',
        ]
        self._mixin_test_table_edit_column(
            'softwarerecipestable',
            'edit-columns-button',
            [f'checkbox-{column}' for column in column_list]
        )
        self._navigate_to_config_nav('softwarerecipestable', 4)
        # check show rows(pagination)
        self._mixin_test_table_show_rows(table_selector='softwarerecipestable')

    def test_machines_page(self):
        """ Test Machine page
            - Check if title "Compatible machines" is displayed
            - Check search input
            - Check "Select machine" button works
            - Check "Add layer" button works
            - Check Machine table feature(show/hide column, pagination)
        """
        self._navigate_to_config_nav('machinestable', 5)
        # check title "Compatible software recipes" is displayed
        self.assertTrue("Compatible machines" in self.get_page_source())
        # Test search input
        self._mixin_test_table_search_input(
            input_selector='search-input-machinestable',
            input_text='qemux86-64',
            searchBtn_selector='search-submit-machinestable',
            table_selector='machinestable'
        )
        # check "Select machine" button works
        rows = self.find_all('#machinestable tbody tr')
        machine_to_select = rows[0]
        select_btn = machine_to_select.find_element(
            By.XPATH,
            '//td[@class="add-del-layers"]'
        )
        select_btn.click()
        self.wait_until_visible('#config-nav')
        project_machine_name = self.find('#project-machine-name')
        self.assertTrue(
            'qemux86-64' in project_machine_name.text
        )
        # check "Add layer" button works
        self._navigate_to_config_nav('machinestable', 5)
        # Search for a machine whit layer not in project
        self._mixin_test_table_search_input(
            input_selector='search-input-machinestable',
            input_text='qemux86-64-screen',
            searchBtn_selector='search-submit-machinestable',
            table_selector='machinestable'
        )
        rows = self.find_all('#machinestable tbody tr')
        machine_to_add = rows[0]
        add_btn = machine_to_add.find_element(
            By.XPATH,
            '//td[@class="add-del-layers"]'
        )
        add_btn.click()
        # check modal is displayed
        self.wait_until_visible('#dependencies-modal')
        list_dependencies = self.find_all('#dependencies-list li')
        # click on add-layers button
        add_layers_btn = self.driver.find_element(
            By.XPATH,
            '//form[@id="dependencies-modal-form"]//button[@class="btn btn-primary"]'
        )
        add_layers_btn.click()
        self.wait_until_visible('#change-notification')
        change_notification = self.find('#change-notification')
        self.assertTrue(
            f'You have added {len(list_dependencies)+1} layers to your project: meta-tanowrt and its dependencies' in change_notification.text
        )

        # check Machine table feature(show/hide column, pagination)
        self._navigate_to_config_nav('machinestable', 5)
        column_list = [
            'description',
            'layer_version__get_vcs_reference',
            'layer_version__layer__name',
            'machinefile',
        ]
        self._mixin_test_table_edit_column(
            'machinestable',
            'edit-columns-button',
            [f'checkbox-{column}' for column in column_list]
        )
        self._navigate_to_config_nav('machinestable', 5)
        # check show rows(pagination)
        self._mixin_test_table_show_rows(table_selector='machinestable')

    def test_layers_page(self):
        """ Test layers page
            - Check if title "Compatible layerss" is displayed
            - Check search input
            - Check "Add layer" button works
            - Check "Remove layer" button works
            - Check layers table feature(show/hide column, pagination)
        """
        self._navigate_to_config_nav('layerstable', 6)
        # check title "Compatible layers" is displayed
        self.assertTrue("Compatible layers" in self.get_page_source())
        # Test search input
        input_text='meta-tanowrt'
        self._mixin_test_table_search_input(
            input_selector='search-input-layerstable',
            input_text=input_text,
            searchBtn_selector='search-submit-layerstable',
            table_selector='layerstable'
        )
        # check "Add layer" button works
        rows = self.find_all('#layerstable tbody tr')
        layer_to_add = rows[0]
        add_btn = layer_to_add.find_element(
            By.XPATH,
            '//td[@class="add-del-layers"]'
        )
        add_btn.click()
        # check modal is displayed
        self.wait_until_visible('#dependencies-modal')
        list_dependencies = self.find_all('#dependencies-list li')
        # click on add-layers button
        add_layers_btn = self.driver.find_element(
            By.XPATH,
            '//form[@id="dependencies-modal-form"]//button[@class="btn btn-primary"]'
        )
        add_layers_btn.click()
        self.wait_until_visible('#change-notification')
        change_notification = self.find('#change-notification')
        self.assertTrue(
            f'You have added {len(list_dependencies)+1} layers to your project: {input_text} and its dependencies' in change_notification.text
        )
        # check "Remove layer" button works
        rows = self.find_all('#layerstable tbody tr')
        layer_to_remove = rows[0]
        remove_btn = layer_to_remove.find_element(
            By.XPATH,
            '//td[@class="add-del-layers"]'
        )
        remove_btn.click()
        self.wait_until_visible('#change-notification', poll=2)
        change_notification = self.find('#change-notification')
        self.assertTrue(
            f'You have removed 1 layer from your project: {input_text}' in change_notification.text
        )
        # check layers table feature(show/hide column, pagination)
        self._navigate_to_config_nav('layerstable', 6)
        column_list = [
            'dependencies',
            'revision',
            'layer__vcs_url',
            'git_subdir',
            'layer__summary',
        ]
        self._mixin_test_table_edit_column(
            'layerstable',
            'edit-columns-button',
            [f'checkbox-{column}' for column in column_list]
        )
        self._navigate_to_config_nav('layerstable', 6)
        # check show rows(pagination)
        self._mixin_test_table_show_rows(table_selector='layerstable')
