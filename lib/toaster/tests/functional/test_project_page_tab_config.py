#! /usr/bin/env python3 #
# BitBake Toaster UI tests implementation
#
# Copyright (C) 2023 Savoir-faire Linux
#
# SPDX-License-Identifier: GPL-2.0-only
#

from time import sleep
import pytest
from django.urls import reverse
from selenium.webdriver import Keys
from selenium.webdriver.support.select import Select
from selenium.common.exceptions import NoSuchElementException
from tests.functional.functional_helpers import SeleniumFunctionalTestCase
from selenium.webdriver.common.by import By


@pytest.mark.django_db
class TestProjectConfigTab(SeleniumFunctionalTestCase):

    def setUp(self):
        self.recipe = None
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

    @classmethod
    def _wait_until_build(cls, state):
        while True:
            try:
                last_build_state = cls.driver.find_element(
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

    def _create_builds(self):
        # check search box can be use to build recipes
        search_box = self.find('#build-input')
        search_box.send_keys('core-image-minimal')
        self.find('#build-button').click()
        sleep(1)
        self.wait_until_visible('#latest-builds')
        # loop until reach the parsing state
        self._wait_until_build('parsing starting cloning')
        lastest_builds = self.driver.find_elements(
            By.XPATH,
            '//div[@id="latest-builds"]/div',
        )
        last_build = lastest_builds[0]
        self.assertTrue(
            'core-image-minimal' in str(last_build.text)
        )
        cancel_button = last_build.find_element(
            By.XPATH,
            '//span[@class="cancel-build-btn pull-right alert-link"]',
        )
        cancel_button.click()
        sleep(1)
        self._wait_until_build('cancelled')

    def _get_tabs(self):
        # tabs links list
        return self.driver.find_elements(
            By.XPATH,
            '//div[@id="project-topbar"]//li'
        )

    def _get_config_nav_item(self, index):
        config_nav = self.find('#config-nav')
        return config_nav.find_elements(By.TAG_NAME, 'li')[index]

    def test_project_config_nav(self):
        """ Test project config tab navigation:
        - Check if the menu is displayed and contains the right elements:
            - Configuration
            - COMPATIBLE METADATA
            - Custom images
            - Image recipes
            - Software recipes
            - Machines
            - Layers
            - Distro
            - EXTRA CONFIGURATION
            - Bitbake variables
            - Actions
            - Delete project
        """
        # navigate to the project page
        url = reverse("project", args=(1,))
        self.get(url)

        # check if the menu is displayed
        self.wait_until_visible('#config-nav')

        def _get_config_nav_item(index):
            config_nav = self.find('#config-nav')
            return config_nav.find_elements(By.TAG_NAME, 'li')[index]

        def check_config_nav_item(index, item_name, url):
            item = _get_config_nav_item(index)
            self.assertTrue(item_name in item.text)
            self.assertTrue(item.get_attribute('class') == 'active')
            self.assertTrue(url in self.driver.current_url)

        # check if the menu contains the right elements
        # COMPATIBLE METADATA
        compatible_metadata = _get_config_nav_item(1)
        self.assertTrue(
            "compatible metadata" in compatible_metadata.text.lower()
        )
        # EXTRA CONFIGURATION
        extra_configuration = _get_config_nav_item(8)
        self.assertTrue(
            "extra configuration" in extra_configuration.text.lower()
        )
        # Actions
        actions = _get_config_nav_item(10)
        self.assertTrue("actions" in str(actions.text).lower())

        conf_nav_list = [
            [0, 'Configuration', f"/toastergui/project/1"],  # config
            [2, 'Custom images', f"/toastergui/project/1/customimages"],  # custom images
            [3, 'Image recipes', f"/toastergui/project/1/images"],  # image recipes
            [4, 'Software recipes', f"/toastergui/project/1/softwarerecipes"],  # software recipes
            [5, 'Machines', f"/toastergui/project/1/machines"],  # machines
            [6, 'Layers', f"/toastergui/project/1/layers"],  # layers
            [7, 'Distro', f"/toastergui/project/1/distro"],  # distro
            [9, 'BitBake variables', f"/toastergui/project/1/configuration"],  # bitbake variables
        ]
        for index, item_name, url in conf_nav_list:
            item = _get_config_nav_item(index)
            if item.get_attribute('class') != 'active':
                item.click()
            check_config_nav_item(index, item_name, url)

    def test_project_config_tab_right_section(self):
        """ Test project config tab right section contains five blocks:
            - Machine:
                - check 'Machine' is displayed
                - check can change Machine
            - Distro:
                - check 'Distro' is displayed
                - check can change Distro
            - Most built recipes:
                - check 'Most built recipes' is displayed
                - check can select a recipe and build it
            - Project release:
                - check 'Project release' is displayed
                - check project has right release displayed
            - Layers:
                - check can add a layer if exists
                - check at least three layers are displayed
                    - openembedded-core
                    - meta-poky
                    - meta-yocto-bsp
        """
        # navigate to the project page
        url = reverse("project", args=(1,))
        self.get(url)

        # check if the menu is displayed
        self.wait_until_visible('#project-page')
        block_l = self.driver.find_element(
            By.XPATH, '//*[@id="project-page"]/div[2]')
        machine = self.find('#machine-section')
        distro = self.find('#distro-section')
        most_built_recipes = self.driver.find_element(
            By.XPATH, '//*[@id="project-page"]/div[1]/div[3]')
        project_release = self.driver.find_element(
            By.XPATH, '//*[@id="project-page"]/div[1]/div[4]')
        layers = block_l.find_element(By.ID, 'layer-container')

        def check_machine_distro(self, item_name, new_item_name, block):
            title = block.find_element(By.TAG_NAME, 'h3')
            self.assertTrue(item_name.capitalize() in title.text)
            edit_btn = block.find_element(By.ID, f'change-{item_name}-toggle')
            edit_btn.click()
            sleep(1)
            name_input = block.find_element(By.ID, f'{item_name}-change-input')
            name_input.clear()
            name_input.send_keys(new_item_name)
            change_btn = block.find_element(By.ID, f'{item_name}-change-btn')
            change_btn.click()
            sleep(1)
            project_name = block.find_element(By.ID, f'project-{item_name}-name')
            self.assertTrue(new_item_name in project_name.text)
            # check change notificaiton is displayed
            change_notification = self.find('#change-notification')
            self.assertTrue(
                f'You have changed the {item_name} to: {new_item_name}' in change_notification.text
            )

        # Machine
        check_machine_distro(self, 'machine', 'qemux86-64', machine)
        # Distro
        check_machine_distro(self, 'distro', 'poky-altcfg', distro)

        # Project release
        title = project_release.find_element(By.TAG_NAME, 'h3')
        self.assertTrue("Project release" in title.text)
        self.assertTrue(
            "Yocto Project master" in self.find('#project-release-title').text
        )

        # Layers
        title = layers.find_element(By.TAG_NAME, 'h3')
        self.assertTrue("Layers" in title.text)
        # check at least three layers are displayed
        # openembedded-core
        # meta-poky
        # meta-yocto-bsp
        layers_list = layers.find_element(By.ID, 'layers-in-project-list')
        layers_list_items = layers_list.find_elements(By.TAG_NAME, 'li')
        self.assertTrue(len(layers_list_items) == 3)
        # check can add a layer if exists
        add_layer_input = layers.find_element(By.ID, 'layer-add-input')
        add_layer_input.send_keys('meta-oe')
        self.wait_until_visible('#layer-container > form > div > span > div')
        dropdown_item = self.driver.find_element(
            By.XPATH,
            '//*[@id="layer-container"]/form/div/span/div'
        )
        dropdown_item.click()
        add_layer_btn = layers.find_element(By.ID, 'add-layer-btn')
        add_layer_btn.click()
        sleep(1)
        # check layer is added
        layers_list_items = layers_list.find_elements(By.TAG_NAME, 'li')
        self.assertTrue(len(layers_list_items) == 4)

        # Most built recipes
        title = most_built_recipes.find_element(By.TAG_NAME, 'h3')
        self.assertTrue("Most built recipes" in title.text)
        # Create a new builds 5
        self._create_builds()

        # Refresh the page
        self.get(url)

        sleep(1)  # wait for page to load
        self.wait_until_visible('#project-page')
        # check can select a recipe and build it
        most_built_recipes = self.driver.find_element(
            By.XPATH, '//*[@id="project-page"]/div[1]/div[3]')
        recipe_list = most_built_recipes.find_element(By.ID, 'freq-build-list')
        recipe_list_items = recipe_list.find_elements(By.TAG_NAME, 'li')
        self.assertTrue(len(recipe_list_items) > 0)
        checkbox = recipe_list_items[0].find_element(By.TAG_NAME, 'input')
        checkbox.click()
        build_btn = self.find('#freq-build-btn')
        build_btn.click()
        sleep(1)  # wait for page to load
        self.wait_until_visible('#latest-builds')
        self._wait_until_build('parsing starting cloning queueing')
        lastest_builds = self.driver.find_elements(
            By.XPATH,
            '//div[@id="latest-builds"]/div'
        )
        last_build = lastest_builds[0]
        cancel_button = last_build.find_element(
            By.XPATH,
            '//span[@class="cancel-build-btn pull-right alert-link"]',
        )
        cancel_button.click()
        self.assertTrue(len(lastest_builds) == 2)

    def test_project_page_tab_importlayer(self):
        """ Test project page tab import layer """
        # navigate to the project page
        url = reverse("project", args=(1,))
        self.get(url)

        # navigate to "Import layers" tab
        import_layers_tab = self._get_tabs()[2]
        import_layers_tab.find_element(By.TAG_NAME, 'a').click()
        self.wait_until_visible('#layer-git-repo-url')

        # Check git repo radio button
        git_repo_radio = self.find('#git-repo-radio')
        git_repo_radio.click()

        # Set git repo url
        input_repo_url = self.find('#layer-git-repo-url')
        input_repo_url.send_keys('git://git.yoctoproject.org/meta-fake')
        # Blur the input to trigger the validation
        input_repo_url.send_keys(Keys.TAB)

        # Check name is set
        input_layer_name = self.find('#import-layer-name')
        self.assertTrue(input_layer_name.get_attribute('value') == 'meta-fake')

        # Set branch
        input_branch = self.find('#layer-git-ref')
        input_branch.send_keys('master')

        # Import layer
        self.find('#import-and-add-btn').click()

        # Check layer is added
        self.wait_until_visible('#layer-container')
        block_l = self.driver.find_element(
            By.XPATH, '//*[@id="project-page"]/div[2]')
        layers = block_l.find_element(By.ID, 'layer-container')
        layers_list = layers.find_element(By.ID, 'layers-in-project-list')
        layers_list_items = layers_list.find_elements(By.TAG_NAME, 'li')
        self.assertTrue(
            'meta-fake' in str(layers_list_items[-1].text)
        )

    def test_project_page_custom_image_no_image(self):
        """ Test project page tab "New custom image" when no custom image """
        # navigate to the project page
        url = reverse("project", args=(1,))
        self.get(url)

        # navigate to "Custom image" tab
        custom_image_section = self._get_config_nav_item(2)
        custom_image_section.click()
        self.wait_until_visible('#empty-state-customimagestable')

        # Check message when no custom image
        self.assertTrue(
            "You have not created any custom images yet." in str(
                self.find('#empty-state-customimagestable').text
            )
        )
        div_empty_msg = self.find('#empty-state-customimagestable')
        link_create_custom_image = div_empty_msg.find_element(
            By.TAG_NAME, 'a')
        self.assertTrue(
            f"/toastergui/project/1/newcustomimage" in str(
                link_create_custom_image.get_attribute('href')
            )
        )
        self.assertTrue(
            "Create your first custom image" in str(
                link_create_custom_image.text
            )
        )