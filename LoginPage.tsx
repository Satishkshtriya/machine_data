import React, { useState } from 'react';
import { Eye, EyeOff, Sparkles, Moon, Sun, LogIn } from 'lucide-react';
import logo from "../images/zeitlogo.png"

interface LoginPageProps {
  onLogin: () => void;
  isDarkMode: boolean;
  setIsDarkMode: (darkMode: boolean) => void;
}

export default function LoginPage({ onLogin, isDarkMode, setIsDarkMode }: LoginPageProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Dummy authentication
    if (email === 'zeit@bot.com' && password === 'zeit123') {
      onLogin();
    } else {
      setError('Invalid email or password. Please try the demo credentials.');
    }
    
    setIsLoading(false);
  };

  const themeClasses = {
    background: isDarkMode ? 'bg-gray-900' : 'bg-gray-50',
    cardBg: isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200',
    text: isDarkMode ? 'text-white' : 'text-gray-800',
    subText: isDarkMode ? 'text-gray-400' : 'text-gray-600',
    inputBg: isDarkMode ? 'bg-gray-700 border-gray-600' : 'bg-white border-gray-300',
    inputText: isDarkMode ? 'text-white placeholder-gray-400' : 'text-gray-800 placeholder-gray-500',
    demoBg: isDarkMode ? 'bg-gray-700 border-gray-600' : 'bg-blue-50 border-blue-200',
    demoText: isDarkMode ? 'text-gray-300' : 'text-blue-800'
  };

  return (
    <div className={`min-h-screen ${themeClasses.background} flex items-center justify-center p-4 transition-colors duration-300`}>
      <div className="w-full max-w-md">
        {/* Header with theme toggle */}
        <div className="flex justify-between items-center mb-8">
          <div className="flex items-center gap-3">
            {/* <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div> */}
            <h1 className={`text-2xl font-bold ${themeClasses.text}`}>
              <img src={logo} alt="zeitlogo(2).png" className="h-[100px] w-auto inline-blockc object-cover" />
            </h1>
          </div>
          <button
            onClick={() => setIsDarkMode(!isDarkMode)}
            className={`p-2 rounded-lg transition-colors ${isDarkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-100'}`}
          >
            {isDarkMode ? <Sun className={`w-5 h-5 ${themeClasses.text}`} /> : <Moon className={`w-5 h-5 ${themeClasses.text}`} />}
          </button>
        </div>

        {/* Login Card */}
      <div
  className={`
    bg-gradient-to-br from-green-200 via-green-400 to-green-600
    bg-opacity-30            
    backdrop-blur-lg         
    border border-white/20 dark:border-gray-700/40
    rounded-2xl shadow-xl p-8
  `}
>

          <div className="text-center mb-8">
            <div className="w-16 h-16 object-cover rounded-2xl flex items-center justify-center mx-auto mb-4">
              {/* <Sparkles className="w-8 h-8 text-white" /> */}
              <img src={logo} alt="zeitlogo.png" className="h-[110px] w-auto inline-block object-cover " />
            </div>
            <h2 className={`text-2xl font-bold ${themeClasses.text} mb-2`}>Welcome </h2>
            <p className={themeClasses.subText}>Sign in to Zeit system bot services</p>
          </div>

          

          <form onSubmit={handleLogin} className="space-y-6">
            {/* Email Field */}
            <div>
              <label className={`block text-sm font-medium ${themeClasses.text} mb-2`}>
                Email Address
              </label>
              <input
                type="email"
                required
                className={`w-full px-4 py-3 rounded-lg border focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all ${themeClasses.inputBg} ${themeClasses.inputText}`}
                placeholder="Enter your email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>

            {/* Password Field */}
            <div>
              <label className={`block text-sm font-medium ${themeClasses.text} mb-2`}>
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  className={`w-full px-4 py-3 pr-12 rounded-lg border focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all ${themeClasses.inputBg} ${themeClasses.inputText}`}
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className={`absolute right-3 top-1/2 transform -translate-y-1/2 ${themeClasses.subText} hover:${themeClasses.text} transition-colors`}
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            {/* Login Button */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-gradient-to-r from-green-900 to-green-900 hover:from-green-900 hover:to-green-700 disabled:from-gray-400 disabled:to-gray-400 text-white py-3 px-4 rounded-lg font-medium transition-all duration-200 flex items-center justify-center gap-2 disabled:cursor-not-allowed transform hover:scale-105 active:scale-95"
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <>
                  <LogIn className="w-5 h-5" />
                  Sign In
                </>
              )}
            </button>
          </form>

          <div className="mt-6 text-center">
            <p className={`text-sm ${themeClasses.subText}`}>
              Secure authentication powered by Zeit system
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}