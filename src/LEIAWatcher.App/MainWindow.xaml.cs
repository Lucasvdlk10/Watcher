using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Windowing;
using Windows.System;
using Microsoft.UI.Xaml.Media.Animation;
using LEIAWatcher.App.Views;
using LEIAWatcher.Domain;
namespace LEIAWatcher.App;
public sealed partial class MainWindow:Window {
 readonly WindowLifetimePolicy lifetime=new();
 readonly System.Windows.Forms.NotifyIcon trayIcon;
 public MainWindow(){InitializeComponent(); ContentFrame.DataContext=App.State; ((FrameworkElement)Content).DataContext=App.State;
  var iconPath=System.IO.Path.Combine(AppContext.BaseDirectory,"Assets","Brand","leia-watcher-eye-radar-v2.ico");
  if(AppWindow is not null){AppWindow.Title="LEIA Watcher";AppWindow.SetIcon(iconPath);AppWindow.Resize(new Windows.Graphics.SizeInt32(1366,768));}
  var menu=new System.Windows.Forms.ContextMenuStrip();
  menu.Items.Add("Abrir LEIA Watcher",null,(_,_)=>ShowFromTray());
  menu.Items.Add(new System.Windows.Forms.ToolStripSeparator());
  menu.Items.Add("Fechar",null,(_,_)=>ExitFromTray());
  trayIcon=new System.Windows.Forms.NotifyIcon {
   Text="LEIA Watcher — organização local ativa",
   Icon=new System.Drawing.Icon(iconPath),
   ContextMenuStrip=menu,
   Visible=true
  };
  trayIcon.DoubleClick+=(_,_)=>ShowFromTray();
  AppWindow.Closing+=OnAppWindowClosing;
  ContentFrame.Navigate(typeof(OverviewPage));
  ((FrameworkElement)Content).KeyDown+=(s,e)=>{if(e.Key==VirtualKey.K && Microsoft.UI.Input.InputKeyboardSource.GetKeyStateForCurrentThread(VirtualKey.Control).HasFlag(Windows.UI.Core.CoreVirtualKeyStates.Down)){GlobalSearch.Focus(FocusState.Keyboard);e.Handled=true;}};
 }
 void Navigate(object sender,RoutedEventArgs e){if(sender is not Button b)return;string tag=b.Tag?.ToString()??"overview";
  var page=tag switch{"folders"=>typeof(FoldersPage),"rules"=>typeof(RulesPage),"files"=>typeof(FilesPage),"history"=>typeof(HistoryPage),"hermes"=>typeof(HermesPage),"settings"=>typeof(SettingsPage),_=>typeof(OverviewPage)};
  NavigatePage(page);
 }
 async void RefreshClicked(object sender,RoutedEventArgs e)=>await App.State.RefreshAsync();
 void SearchChanged(object sender,TextChangedEventArgs e){App.State.Search=GlobalSearch.Text;}
 public void Show(string destination){NavigatePage(destination switch{"folders"=>typeof(FoldersPage),"rules"=>typeof(RulesPage),"files"=>typeof(FilesPage),"history"=>typeof(HistoryPage),"hermes"=>typeof(HermesPage),"settings"=>typeof(SettingsPage),_=>typeof(OverviewPage)});}
 void NavigatePage(Type page){if(App.State.Motion=="Desligada")ContentFrame.Navigate(page,null,new SuppressNavigationTransitionInfo());else ContentFrame.Navigate(page,null,new EntranceNavigationTransitionInfo());}
 void OnAppWindowClosing(AppWindow sender,AppWindowClosingEventArgs args){
  if(lifetime.OnWindowCloseRequested()==WindowCloseAction.Exit)return;
  args.Cancel=true;
  sender.Hide();
  trayIcon.ShowBalloonTip(1800,"LEIA Watcher","O Watcher continua ativo nos ícones ocultos.",System.Windows.Forms.ToolTipIcon.Info);
 }
 void ShowFromTray()=>DispatcherQueue.TryEnqueue(()=>{AppWindow.Show();Activate();});
 void ExitFromTray()=>DispatcherQueue.TryEnqueue(()=>{
  lifetime.RequestExit();
  trayIcon.Visible=false;
  trayIcon.Dispose();
  Close();
 });
}
