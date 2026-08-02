import { AbilityConstant, Configuration, ConfigurationConstant, UIAbility, Want } from '@kit.AbilityKit';
import { hilog } from '@kit.PerformanceAnalysisKit';
import { window } from '@kit.ArkUI';
import { SystemBar } from '../utils/SystemBar';
import font from '@ohos.font';
import preferences from '@ohos.data.preferences';

const DOMAIN = 0x0000;

export default class EntryAbility extends UIAbility {
  onCreate(want: Want, launchParam: AbilityConstant.LaunchParam): void {
    try {
      this.context.getApplicationContext().setColorMode(ConfigurationConstant.ColorMode.COLOR_MODE_NOT_SET);
    } catch (err) {
      hilog.error(DOMAIN, 'testTag', 'Failed to set colorMode. Cause: %{public}s', JSON.stringify(err));
    }
    // AppStorage初始化必须在组件加载前完成，否则@StorageLink会因key不存在崩溃
    AppStorage.setOrCreate('themeMode', 'system');
    AppStorage.setOrCreate('fontScale', 1);
    AppStorage.setOrCreate('language', 'zh');
    AppStorage.setOrCreate('styleMode', 'glass');
    // 注册 Inter 字体（Claude 风格）
    try {
      font.registerFont({ familyName: 'Inter', familySrc: '/rawfile/fonts/Inter-Regular.ttf' });
      font.registerFont({ familyName: 'InterBold', familySrc: '/rawfile/fonts/Inter-SemiBold.ttf' });
    } catch (e) {
      // 忽略
    }
    // 记录系统当前深浅色，供"跟随系统"模式使用
    let isDark = this.context.config.colorMode === ConfigurationConstant.ColorMode.COLOR_MODE_DARK;
    AppStorage.setOrCreate('systemDark', isDark);
    hilog.info(DOMAIN, 'testTag', '%{public}s', 'Ability onCreate');
  }

  onConfigurationUpdate(newConfig: Configuration) {
    // 系统深浅色切换 → 更新"跟随系统"模式并同步系统栏颜色
    let isDark = newConfig.colorMode === ConfigurationConstant.ColorMode.COLOR_MODE_DARK;
    AppStorage.setOrCreate('systemDark', isDark);
    SystemBar.apply();
  }

  onDestroy(): void {
    hilog.info(DOMAIN, 'testTag', '%{public}s', 'Ability onDestroy');
  }

  async onWindowStageCreate(windowStage: window.WindowStage): Promise<void> {
    hilog.info(DOMAIN, 'testTag', '%{public}s', 'Ability onWindowStageCreate');

    // 从 Preferences 恢复用户设置（异步，@StorageLink 会自动刷新 UI）
    try {
      let pref = await preferences.getPreferences(this.context, 'smartkitchen_settings')
      let mode = await pref.get('themeMode', 'system') as string
      let scale = await pref.get('fontScale', 1) as number
      let lang = await pref.get('language', 'zh') as string
      let style = await pref.get('styleMode', 'glass') as string
      AppStorage.setOrCreate('themeMode', mode)
      AppStorage.setOrCreate('fontScale', scale)
      AppStorage.setOrCreate('language', lang)
      AppStorage.setOrCreate('styleMode', style)
      // 同步应用级颜色模式（sys.color 系统资源文字跟随 App 主题解析）
      SystemBar.applyColorMode(this.context, mode)
    } catch (e) {
      // 首次启动无设置文件
    }

    // 系统栏颜色与页面背景同步（无白边沉浸式）
    // 必须在 loadContent 成功后再取主窗口，否则 setWindowSystemBarProperties 会静默失败 → 状态栏/导航栏留白条
    windowStage.loadContent('pages/Index', (err) => {
      if (err.code) {
        hilog.error(DOMAIN, 'testTag', 'Failed to load the content. Cause: %{public}s', JSON.stringify(err));
        return;
      }
      hilog.info(DOMAIN, 'testTag', 'Succeeded in loading the content.');
      windowStage.getMainWindow().then((win) => {
        SystemBar.init(win)
      })
    });
  }

  onWindowStageDestroy(): void {
    hilog.info(DOMAIN, 'testTag', '%{public}s', 'Ability onWindowStageDestroy');
  }

  onForeground(): void {
    hilog.info(DOMAIN, 'testTag', '%{public}s', 'Ability onForeground');
  }

  onBackground(): void {
    hilog.info(DOMAIN, 'testTag', '%{public}s', 'Ability onBackground');
  }
}
