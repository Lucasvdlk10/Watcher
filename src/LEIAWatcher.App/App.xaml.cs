using LEIAWatcher.App.ViewModels;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Media;
using Microsoft.UI.Composition.SystemBackdrops;
namespace LEIAWatcher.App;
public partial class App:Application {
 public static MainWindow? Main {get;private set;}
 public static WatcherViewModel State {get;}=new();
 static readonly string StartupLog=System.IO.Path.Combine(System.IO.Path.GetTempPath(),"leia-watcher-winui4-startup.log");
 static void Log(string text)=>System.IO.File.AppendAllText(StartupLog,$"{DateTime.Now:O} {text}{Environment.NewLine}");
 public App(){
  try { Log("App ctor begin"); InitializeComponent(); Log("App XAML initialized"); }
  catch(Exception ex){Log("App InitializeComponent failed: "+ex);throw;}
  UnhandledException+=(s,e)=>{Log("Unhandled: "+e.Exception);};
 }
 protected override void OnLaunched(LaunchActivatedEventArgs args){
  try {Log("OnLaunched begin");Main=new MainWindow();Log("MainWindow created");Main.Activate();Log("MainWindow activated");_=State.RefreshAsync();}
  catch(Exception ex){Log("OnLaunched failed: "+ex);throw;}
 }
}
