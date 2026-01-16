# iOS Development Build Guide (Mac)

This guide walks you through creating a development build for iPad using a Mac. After this one-time setup, you can develop from any machine (like your Ubuntu server) - the Mac is only needed occasionally.

## What You'll Get

- An app installed directly on your iPad
- No more Expo Go limitations (touch blocking issues, new architecture bugs)
- Normal hot-reload development from your Ubuntu server via tunnel

---

## Prerequisites (One-Time Mac Setup)

### Step 1: Install Xcode

**Time: 10-20 minutes (large download)**

1. Open the **App Store** on the Mac
2. Search for "Xcode"
3. Click **Get/Install** (it's free but ~12GB)
4. Wait for download and installation
5. Open Xcode once and accept the license agreement when prompted

### Step 2: Install Xcode Command Line Tools

Open **Terminal** (press `Cmd + Space`, type "Terminal", press Enter):

```bash
xcode-select --install
```

A popup will appear - click **Install** and wait for it to complete.

### Step 3: Install Homebrew

Homebrew is a package manager for Mac. In Terminal:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**Important**: At the end, it may print instructions to add Homebrew to your PATH. Follow those instructions (usually involves running two commands it shows you).

### Step 4: Install Node.js

```bash
brew install node
```

Verify it worked:

```bash
node --version
```

Should print something like `v20.x.x` or `v22.x.x`.

### Step 5: Install CocoaPods

CocoaPods manages iOS native dependencies:

```bash
sudo gem install cocoapods
```

Enter your Mac password when prompted (you won't see characters as you type - that's normal).

---

## Build the App

### Step 6: Clone the Repository

```bash
cd ~
git clone git@github.com:YOUR_USERNAME/childrens_stories.git
cd childrens_stories/frontend
```

Replace `YOUR_USERNAME` with your GitHub username.

If you already have it cloned, just pull the latest:

```bash
cd ~/childrens_stories
git pull
cd frontend
```

### Step 7: Install Dependencies

```bash
npm install
```

This installs all the JavaScript packages. Takes 1-2 minutes.

### Step 8: Connect Your iPad

1. Connect iPad to Mac with a USB cable (Lightning or USB-C)
2. **On iPad**: Tap **Trust** when the "Trust This Computer?" popup appears
3. Enter your iPad passcode if prompted
4. If Finder or iTunes opens, you can close it

### Step 9: Build and Install

Run this command:

```bash
npx expo run:ios --device
```

**What happens:**

1. **Device selection**: Use arrow keys to select your iPad, press Enter
2. **Native project generation**: Creates the `ios/` folder (~1 min)
3. **CocoaPods install**: Downloads iOS dependencies (~2 min)
4. **Xcode build**: Compiles the app (~5-10 min first time, faster after)
5. **Installation**: Copies app to your iPad

**You may be prompted for:**

- **Apple ID**: Sign in with any Apple ID (doesn't need to be a paid developer account)
- **Team selection**: Choose your personal team / Apple ID

### Step 10: Trust the Developer on iPad

The first time you install, iPad won't let you open the app. Fix this:

1. On iPad, open **Settings**
2. Go to **General → VPN & Device Management**
3. Under "Developer App", you'll see an email (your Apple ID)
4. Tap on it
5. Tap **Trust "[your email]"**
6. Tap **Trust** in the confirmation popup

### Step 11: Verify the App Works

1. Find the app on your iPad home screen (it's called "expo-nativewind-test")
2. Tap to open it
3. You should see a loading screen or the app UI

---

## Daily Development (From Ubuntu Server)

Once the app is installed on your iPad, you don't need the Mac anymore for normal development.

### On your Ubuntu server:

```bash
cd /home/kavin/childrens_stories/frontend
npx expo start --tunnel --dev-client
```

**Note the `--dev-client` flag** - this is important! It tells Expo you're using a development build instead of Expo Go.

### On your iPad:

1. Open your installed app (NOT Expo Go)
2. You'll see a developer menu with options to enter a URL or scan QR code
3. Scan the QR code shown in your terminal

You're now connected! Changes you make on Ubuntu will hot-reload on the iPad.

---

## When You Need the Mac Again

You'll need to rebuild on the Mac when:

| Change | Rebuild needed? |
|--------|-----------------|
| JavaScript/TypeScript code changes | No |
| Adding JS-only npm packages | No |
| Adding packages with native code | **Yes** |
| Updating Expo SDK version | **Yes** |
| Changing `app.json` iOS settings | **Yes** |

To rebuild, just run `npx expo run:ios --device` again. Subsequent builds are faster (~2-3 min).

---

## Troubleshooting

### "No devices found"

- Make sure iPad is connected via USB
- Check that you tapped "Trust" on the iPad
- Try a different USB port or cable
- Run `xcrun xctrace list devices` to see if Mac detects the iPad

### "Signing requires a development team"

- Xcode will prompt you to sign in with an Apple ID
- Any free Apple ID works - you don't need a paid developer account
- Go to Xcode → Preferences → Accounts → Add your Apple ID

### App crashes immediately on launch

- Make sure you're using `--dev-client` flag when starting Expo
- Check that the Metro bundler is running on Ubuntu

### "Unable to install app"

- iPad might be out of storage - check Settings → General → iPad Storage
- Try disconnecting and reconnecting the iPad
- Restart Xcode and try again

### "Developer is not trusted"

- See Step 10 above - you need to trust the developer in iPad Settings

### Build fails with CocoaPods error

Try cleaning and reinstalling:

```bash
cd ios
rm -rf Pods Podfile.lock
pod install
cd ..
npx expo run:ios --device
```

---

## Removing Expo Go

Once you have the development build working, you can delete Expo Go from your iPad - you won't need it anymore.

---

## Summary

1. **One-time**: Install Xcode, Homebrew, Node, CocoaPods on Mac
2. **One-time**: Build and install app with `npx expo run:ios --device`
3. **Daily**: Develop from Ubuntu with `npx expo start --tunnel --dev-client`
4. **Occasional**: Rebuild on Mac when adding native modules or updating Expo
